import json
import os
from datetime import date
from math import ceil

from backend.allergens import recipe_blocked

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

DAYS_NAMES = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
SLOTS = ["Frühstück", "Mittagessen", "Abendessen"]
PIECE_FALLBACK = {"Eier", "Avocado", "Zitrone"}


def load_json_file(name):
    path = os.path.join(DATA_DIR, name)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_data():
    return (
        load_json_file("recipes.json"),
        load_json_file("prices.json"),
        load_json_file("deals.json"),
        load_json_file("pack_sizes.json"),
    )


RECIPES, PRICES, DEALS, PACK_SIZES = load_data()


def _store_deals(store):
    if isinstance(DEALS, dict) and "stores" in DEALS:
        return DEALS.get("stores", {}).get(store, [])
    return DEALS.get(store, []) if isinstance(DEALS, dict) else []


def deal_week():
    if isinstance(DEALS, dict) and "week" in DEALS:
        return DEALS["week"]
    return ""


def pack_info(ingredient):
    global PACK_SIZES
    if not PACK_SIZES:
        PACK_SIZES = load_json_file("pack_sizes.json")
    info = PACK_SIZES.get(ingredient) or {}
    unit = info.get("unit", "Stück" if ingredient in PIECE_FALLBACK else "g")
    pack_size = info.get("pack_size", 1 if unit == "Stück" else 100)
    aisle = info.get("aisle", "Sonstiges")
    return pack_size, unit, aisle


def is_piece_unit(ingredient):
    _, unit, _ = pack_info(ingredient)
    return unit == "Stück"


def nice_quantity(qty, unit):
    """Cookable amounts: whole grams/ml, pieces at most one decimal."""
    if qty is None or qty <= 0:
        return 0
    if unit == "Stück":
        rounded = round(float(qty), 1)
        if abs(rounded - round(rounded)) < 1e-9:
            return int(round(rounded))
        return rounded
    return max(1, int(round(float(qty))))


def get_ingredient_pricing(ingredient, store):
    """
    Returns (effective_price, regular_price, is_deal, deal_badge, discount_percent).
    regular_price is None when the SKU is missing from the store price list.
    Price is per 100g/ml or per piece.
    """
    deal_info = next(
        (d for d in _store_deals(store) if d["ingredient"].lower() == ingredient.lower()),
        None,
    )
    store_prices = PRICES.get(store, {})
    if ingredient not in store_prices:
        if deal_info:
            return (
                deal_info["offer_price"],
                deal_info.get("regular_price"),
                True,
                deal_info.get("badge", "Angebot"),
                deal_info.get("discount_percent", 25),
            )
        return (0.0, None, False, None, 0)

    regular_price = store_prices[ingredient]
    if deal_info:
        return (
            deal_info["offer_price"],
            deal_info.get("regular_price", regular_price),
            True,
            deal_info.get("badge", "Angebot"),
            deal_info.get("discount_percent", 25),
        )
    return (regular_price, regular_price, False, None, 0)


def evaluate_recipe(recipe, store, pantry_items=None, portions=1):
    """
    Calculates cost, savings, and deal details for a recipe.
    Macros stay per person; quantities and cost scale with portions.
    """
    if pantry_items is None:
        pantry_items = []
    pantry_set = {item.strip().lower() for item in pantry_items}
    portions = max(1, int(portions))

    cost = 0.0
    regular_cost = 0.0
    deal_savings = 0.0
    pantry_savings = 0.0
    deal_items_count = 0
    ingredients_detail = []

    for ing, qty in recipe["ingredients"].items():
        _, unit, aisle = pack_info(ing)
        scaled_qty = nice_quantity(qty * portions, unit)
        eff_price, reg_price, is_deal, badge, discount = get_ingredient_pricing(ing, store)
        is_in_pantry = ing.lower() in pantry_set
        price_missing = reg_price is None

        if is_piece_unit(ing):
            unit_factor = scaled_qty
        else:
            unit_factor = scaled_qty / 100.0

        item_regular = 0.0 if price_missing else unit_factor * reg_price
        item_discounted = 0.0 if price_missing else unit_factor * eff_price

        if is_in_pantry:
            item_effective = 0.0
            pantry_savings += item_discounted
        else:
            item_effective = item_discounted
            if is_deal and not price_missing:
                deal_savings += item_regular - item_discounted
                deal_items_count += 1

        cost += item_effective
        regular_cost += item_regular

        ingredients_detail.append({
            "name": ing,
            "quantity": scaled_qty,
            "unit": unit,
            "is_deal": is_deal,
            "deal_badge": badge,
            "discount_percent": discount,
            "in_pantry": is_in_pantry,
            "item_cost": round(item_effective, 2),
            "aisle": aisle,
            "price_missing": price_missing,
            "effective_price": eff_price if not price_missing else None,
            "regular_price": reg_price,
        })

    return {
        "cost": round(cost, 2),
        "regular_cost": round(regular_cost, 2),
        "deal_savings": round(deal_savings, 2),
        "pantry_savings": round(pantry_savings, 2),
        "deal_items_count": deal_items_count,
        "ingredients_detail": ingredients_detail,
    }


def get_recipe_lucide_icon(recipe):
    name = recipe.get("name", "").lower()
    cat = recipe.get("category", "")
    if any(w in name for w in ["shake", "smoothie", "becher"]):
        return "cup-soda"
    if any(w in name for w in ["haferflocken", "haferbrei", "oats", "bowl", "porridge"]):
        return "coffee"
    if any(w in name for w in ["rührei", "eier", "scramble", "omelett"]):
        return "egg"
    if any(w in name for w in ["lachs", "thunfisch", "fisch"]):
        return "fish"
    if any(w in name for w in ["hähnchen", "pute", "steak", "hackfleisch", "gratin"]):
        return "drumstick"
    if any(w in name for w in ["curry", "suppe", "eintopf"]):
        return "soup"
    if any(w in name for w in ["salat"]):
        return "salad"
    if any(w in name for w in ["pasta", "bolognese", "chili"]):
        return "utensils"
    if cat == "Frühstück":
        return "sun"
    if cat == "Mittagessen":
        return "utensils"
    return "moon"


def meal_from_recipe(recipe, evaluation, category=None):
    return {
        "id": recipe["id"],
        "name": recipe["name"],
        "category": category or recipe.get("category", ""),
        "prep_time": recipe.get("prep_time", "15 Min"),
        "icon": recipe.get("icon", "🍽️"),
        "lucide_icon": get_recipe_lucide_icon(recipe),
        "cost": evaluation["cost"],
        "regular_cost": evaluation["regular_cost"],
        "deal_savings": evaluation["deal_savings"],
        "has_deal": evaluation["deal_items_count"] > 0,
        "macros": recipe["macros"],
        "ingredients": evaluation["ingredients_detail"],
        "instructions": recipe.get("instructions", ""),
        "status": None,
    }


def reload_data():
    global RECIPES, PRICES, DEALS, PACK_SIZES
    RECIPES, PRICES, DEALS, PACK_SIZES = load_data()


def _scale_recipe(recipe, factor):
    if abs(factor - 1.0) < 0.02:
        return recipe
    scaled = dict(recipe)
    scaled["ingredients"] = {k: v * factor for k, v in recipe["ingredients"].items()}
    scaled["macros"] = {k: int(round(v * factor)) for k, v in recipe["macros"].items()}
    return scaled


def _calorie_factor(target_calories):
    return min(1.5, max(0.9, float(target_calories) / 1550.0))


def _eligible_recipes(diet, catalog=None):
    catalog = catalog if catalog is not None else RECIPES
    if diet == "All":
        return list(catalog)
    matched = [r for r in catalog if diet in r.get("diets", [])]
    return matched or list(catalog)


def _recipes_by_slot(recipes):
    grouped = {slot: [r for r in recipes if r.get("category") == slot] for slot in SLOTS}
    for slot in SLOTS:
        if not grouped[slot]:
            grouped[slot] = list(recipes)
    return grouped


def rolling_day_names(days, start=None):
    start = date.today().weekday() if start is None else int(start)
    return [DAYS_NAMES[(start + i) % 7] for i in range(days)]


def _solve_assignment(
    by_slot,
    evals,
    by_id,
    days,
    budget,
    target_calories,
    target_protein,
    max_uses,
    enforce_budget,
    enforce_macros,
    locked=None,
    forbidden=None,
):
    import pulp

    locked = locked or {}
    forbidden = forbidden or {}
    prob = pulp.LpProblem("nutrimatch_plan", pulp.LpMinimize)
    x = {}

    for d in range(days):
        for slot in SLOTS:
            for recipe in by_slot[slot]:
                rid = recipe["id"]
                if (d, slot) in locked and rid != locked[(d, slot)]:
                    continue
                if rid in forbidden.get((d, slot), set()):
                    continue
                x[(d, slot, rid)] = pulp.LpVariable(
                    f"x_{d}_{SLOTS.index(slot)}_{rid}",
                    lowBound=0,
                    upBound=1,
                    cat="Binary",
                )

    for d in range(days):
        for slot in SLOTS:
            vars_ds = [var for (dd, ss, _), var in x.items() if dd == d and ss == slot]
            if not vars_ds:
                return None
            prob += pulp.lpSum(vars_ds) == 1

    recipe_ids = {rid for (_, _, rid) in x}
    repeat_penalties = []
    for rid in recipe_ids:
        vars_r = [var for (d, slot, rr), var in x.items() if rr == rid]
        if not vars_r:
            continue
        if max_uses is not None:
            prob += pulp.lpSum(vars_r) <= max_uses
        extra = pulp.LpVariable(f"extra_{rid}", lowBound=0)
        prob += extra >= pulp.lpSum(vars_r) - 1
        repeat_penalties.append(extra)

    week_cost = pulp.lpSum(
        var * evals[rid]["cost"] for (d, slot, rid), var in x.items()
    )
    if enforce_budget:
        prob += week_cost <= float(budget)

    cal_dev = []
    prot_dev = []
    for d in range(days):
        c_d = pulp.lpSum(
            var * by_id[rid]["macros"]["calories"]
            for (dd, slot, rid), var in x.items()
            if dd == d
        )
        p_d = pulp.lpSum(
            var * by_id[rid]["macros"]["protein"]
            for (dd, slot, rid), var in x.items()
            if dd == d
        )
        cal_pos = pulp.LpVariable(f"cal_pos_{d}", lowBound=0)
        cal_neg = pulp.LpVariable(f"cal_neg_{d}", lowBound=0)
        prot_pos = pulp.LpVariable(f"prot_pos_{d}", lowBound=0)
        prot_neg = pulp.LpVariable(f"prot_neg_{d}", lowBound=0)
        prob += c_d - target_calories == cal_pos - cal_neg
        prob += p_d - target_protein == prot_pos - prot_neg
        cal_dev.extend([cal_pos, cal_neg])
        prot_dev.extend([prot_pos, prot_neg])
        if enforce_macros:
            prob += c_d >= 0.85 * target_calories
            prob += c_d <= 1.15 * target_calories
            prob += p_d >= 0.85 * target_protein
            prob += p_d <= 1.15 * target_protein

    deal_bonus = pulp.lpSum(
        var * evals[rid]["deal_items_count"] for (d, slot, rid), var in x.items()
    )
    prob += (
        4.0 * pulp.lpSum(cal_dev)
        + 6.0 * pulp.lpSum(prot_dev)
        + 1.0 * week_cost
        - 3.0 * deal_bonus
        + 500.0 * pulp.lpSum(repeat_penalties)
    )

    status = prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=3))
    if pulp.LpStatus[status] != "Optimal":
        return None

    picks = {}
    for (d, slot, rid), var in x.items():
        if var.value() is not None and var.value() > 0.5:
            picks[(d, slot)] = rid
    if len(picks) != days * len(SLOTS):
        return None
    return picks


def _greedy_fill(by_slot, days, locked=None, forbidden=None):
    locked = locked or {}
    forbidden = forbidden or {}
    picks = {}
    usage = {}
    for d in range(days):
        for slot in SLOTS:
            if (d, slot) in locked:
                picks[(d, slot)] = locked[(d, slot)]
                usage[locked[(d, slot)]] = usage.get(locked[(d, slot)], 0) + 1
                continue
            candidates = [
                r for r in by_slot[slot]
                if r["id"] not in forbidden.get((d, slot), set())
            ]
            if not candidates:
                candidates = list(by_slot[slot])
            candidates = sorted(candidates, key=lambda r: usage.get(r["id"], 0))
            rid = candidates[0]["id"]
            picks[(d, slot)] = rid
            usage[rid] = usage.get(rid, 0) + 1
    return picks


def _assemble_plan(
    picks,
    store,
    diet,
    budget,
    days,
    target_calories,
    target_protein,
    pantry,
    portions,
    relaxations,
    evals,
    by_id,
    exclude=None,
    day_names=None,
    user_locked=None,
    members=None,
    banned_ids=None,
):
    from backend.shopping import build_shopping_list

    exclude = list(exclude or [])
    user_locked = user_locked or set()
    day_names = day_names or rolling_day_names(days)
    members = list(members or [])
    banned_ids = list(banned_ids or [])

    days_plan = []
    total_cals = total_prot = total_carbs = total_fat = 0
    recipe_line_cost = 0.0
    regular_cost = 0.0
    deal_savings = 0.0
    pantry_savings = 0.0

    for d in range(days):
        meals = []
        day_cost = 0.0
        day_cals = 0
        day_prot = 0
        for slot in SLOTS:
            rid = picks[(d, slot)]
            recipe = by_id[rid]
            ev = evals[rid]
            meal = meal_from_recipe(recipe, ev, slot)
            meal["locked"] = (d, slot) in user_locked
            meals.append(meal)
            day_cost += ev["cost"]
            recipe_line_cost += ev["cost"]
            regular_cost += ev["regular_cost"]
            deal_savings += ev["deal_savings"]
            pantry_savings += ev["pantry_savings"]
            day_cals += recipe["macros"]["calories"]
            day_prot += recipe["macros"]["protein"]
            total_carbs += recipe["macros"]["carbs"]
            total_fat += recipe["macros"]["fat"]
        total_cals += day_cals
        total_prot += day_prot
        days_plan.append({
            "day_index": d,
            "day_name": day_names[d] if d < len(day_names) else DAYS_NAMES[d % len(DAYS_NAMES)],
            "cost": round(day_cost, 2),
            "calories": day_cals,
            "protein": day_prot,
            "meals": meals,
        })

    shopping = build_shopping_list(days_plan, store)
    total_cost = shopping["pack_cost"]
    over_budget = total_cost > float(budget)
    combined_savings = round(max(0.0, (regular_cost + pantry_savings) - recipe_line_cost), 2)

    return {
        "status": "success",
        "store": store,
        "diet": diet,
        "days": days,
        "budget": float(budget),
        "portions": portions,
        "target_calories": int(target_calories),
        "target_protein": int(target_protein),
        "deal_week": deal_week(),
        "total_cost": total_cost,
        "regular_cost": round(regular_cost, 2),
        "deal_savings": round(deal_savings, 2),
        "pantry_savings": round(pantry_savings, 2),
        "combined_savings": combined_savings,
        "budget_percent": min(100, round((total_cost / budget) * 100)) if budget > 0 else 0,
        "over_budget": over_budget,
        "relaxations": relaxations,
        "daily_avg": {
            "calories": round(total_cals / days),
            "protein": round(total_prot / days),
            "carbs": round(total_carbs / days),
            "fat": round(total_fat / days),
        },
        "days_plan": days_plan,
        "shopping_list": shopping,
        "pantry_items": list(pantry),
        "exclude": exclude,
        "members": members,
        "banned_ids": banned_ids,
        "recipe_cost": round(recipe_line_cost, 2),
        "checkout_cost": total_cost,
    }


def _solve_week(
    store,
    diet,
    line_budget,
    days,
    target_calories,
    target_protein,
    pantry,
    portions,
    locked,
    forbidden,
    exclude,
    catalog,
    banned_ids=None,
):
    banned_ids = set(banned_ids or [])
    catalog = [r for r in catalog if r.get("id") not in banned_ids]
    valid = [r for r in _eligible_recipes(diet, catalog) if not recipe_blocked(r, exclude)]
    if not valid:
        valid = [r for r in catalog if not recipe_blocked(r, exclude)]
    if not valid:
        valid = list(catalog)
    by_slot = _recipes_by_slot(valid)
    by_id = {r["id"]: r for r in catalog}
    evals = {r["id"]: evaluate_recipe(r, store, pantry, portions) for r in catalog}

    attempts = [
        (1, True, True, None),
        (1, False, True, "budget"),
        (1, False, False, "macros"),
        (2, False, False, "variety"),
    ]
    relaxations = []
    picks = None
    for i, (max_uses, enforce_budget, enforce_macros, tag) in enumerate(attempts):
        if i > 0 and tag and tag not in relaxations:
            relaxations.append(tag)
        picks = _solve_assignment(
            by_slot,
            evals,
            by_id,
            days,
            line_budget,
            target_calories,
            target_protein,
            max_uses,
            enforce_budget,
            enforce_macros,
            locked=locked,
            forbidden=forbidden,
        )
        if picks is not None:
            break
    if picks is None:
        picks = _greedy_fill(by_slot, days, locked=locked, forbidden=forbidden)
        for extra in ("variety", "budget", "macros"):
            if extra not in relaxations:
                relaxations.append(extra)
    return picks, relaxations, evals, by_id


def generate_meal_plan(
    store="REWE",
    diet="All",
    budget=50.0,
    days=7,
    target_calories=2200,
    target_protein=140,
    pantry=None,
    portions=1,
    locked=None,
    forbidden=None,
    exclude=None,
    day_names=None,
    user_locked=None,
    banned_ids=None,
    members=None,
):
    reload_data()
    if pantry is None:
        pantry = []
    exclude = list(exclude or [])
    banned_ids = list(banned_ids or [])
    members = list(members or [])
    portions = max(1, int(portions))
    days = int(days)
    locked = locked or {}
    forbidden = forbidden or {}
    user_locked = user_locked or set()
    day_names = day_names or rolling_day_names(days)

    factor = _calorie_factor(target_calories)
    catalog = [_scale_recipe(r, factor) for r in RECIPES]

    line_budget = float(budget)
    last_plan = None
    for _ in range(3):
        picks, relaxations, evals, by_id = _solve_week(
            store,
            diet,
            line_budget,
            days,
            target_calories,
            target_protein,
            pantry,
            portions,
            locked,
            forbidden,
            exclude,
            catalog,
            banned_ids=banned_ids,
        )
        plan = _assemble_plan(
            picks,
            store,
            diet,
            budget,
            days,
            target_calories,
            target_protein,
            pantry,
            portions,
            relaxations,
            evals,
            by_id,
            exclude=exclude,
            day_names=day_names,
            user_locked=user_locked,
            members=members,
            banned_ids=banned_ids,
        )
        last_plan = plan
        pack = float(plan["total_cost"])
        if pack <= float(budget) + 0.05:
            plan["over_budget"] = False
            return plan
        if pack <= 0:
            break
        line_budget = max(8.0, line_budget * 0.88 * (float(budget) / pack))

    if last_plan is not None:
        last_plan["over_budget"] = last_plan["total_cost"] > float(budget)
        if last_plan["over_budget"] and "budget" not in last_plan["relaxations"]:
            last_plan["relaxations"].append("budget")
        return last_plan
    raise RuntimeError("meal plan failed")


def swap_single_meal(plan, day_index, category, current_id):
    user_locked = set()
    locked = {}
    for day in plan["days_plan"]:
        for meal in day["meals"]:
            key = (day["day_index"], meal["category"])
            locked[key] = meal["id"]
            if meal.get("locked"):
                user_locked.add(key)
    if (day_index, category) in user_locked:
        return None
    locked.pop((day_index, category), None)
    forbidden = {(day_index, category): {current_id}}
    day_names = [d["day_name"] for d in plan["days_plan"]]

    new_plan = generate_meal_plan(
        store=plan.get("store", "Lidl"),
        diet=plan.get("diet", "All"),
        budget=plan.get("budget", 50),
        days=plan.get("days", len(plan["days_plan"])),
        target_calories=plan.get("target_calories", 2200),
        target_protein=plan.get("target_protein", 140),
        pantry=plan.get("pantry_items") or [],
        portions=plan.get("portions", 1),
        locked=locked,
        forbidden=forbidden,
        exclude=plan.get("exclude") or [],
        day_names=day_names,
        user_locked=user_locked,
        banned_ids=plan.get("banned_ids") or [],
        members=plan.get("members") or [],
    )
    new_id = new_plan["days_plan"][day_index]["meals"][
        SLOTS.index(category)
    ]["id"]
    if new_id == current_id:
        # Try any recipe in the same category, ignoring diet.
        factor = _calorie_factor(new_plan.get("target_calories", 2200))
        catalog = [_scale_recipe(r, factor) for r in RECIPES]
        all_in_slot = [r for r in catalog if r.get("category") == category and r["id"] != current_id]
        if not all_in_slot:
            return None
        valid = _eligible_recipes("All", catalog)
        by_slot_full = _recipes_by_slot(valid)
        by_slot_full[category] = all_in_slot
        evals = {
            r["id"]: evaluate_recipe(
                r,
                new_plan["store"],
                new_plan.get("pantry_items") or [],
                new_plan.get("portions", 1),
            )
            for r in catalog
        }
        by_id = {r["id"]: r for r in catalog}
        picks = _solve_assignment(
            by_slot_full,
            evals,
            by_id,
            new_plan["days"],
            new_plan["budget"],
            new_plan["target_calories"],
            new_plan["target_protein"],
            max_uses=None,
            enforce_budget=False,
            enforce_macros=False,
            locked=locked,
            forbidden=forbidden,
        )
        if picks is None:
            picks = _greedy_fill(by_slot_full, new_plan["days"], locked=locked, forbidden=forbidden)
        if picks[(day_index, category)] == current_id:
            return None
        return _assemble_plan(
            picks,
            new_plan["store"],
            new_plan["diet"],
            new_plan["budget"],
            new_plan["days"],
            new_plan["target_calories"],
            new_plan["target_protein"],
            new_plan.get("pantry_items") or [],
            new_plan.get("portions", 1),
            new_plan.get("relaxations") or [],
            evals,
            by_id,
            exclude=new_plan.get("exclude") or [],
            day_names=day_names,
            user_locked=user_locked,
            members=new_plan.get("members") or [],
        )
    return new_plan

