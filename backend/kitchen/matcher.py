from backend.kitchen.constants import DAY_NAMES, SLOTS, STORES
from backend.kitchen.models import Recipe
from backend.kitchen.resolve import resolve_ingredient
from backend.kitchen.shopping import aggregate_ingredients, recipe_approx_cost
from backend.kitchen.shoppable import is_shoppable, shoppable_recipe_ids, ten_minute_lane


class MatchError(ValueError):
    def __init__(self, code, message=None):
        super().__init__(message or code)
        self.code = code


def _recipe_equipment(recipe):
    tools = list(recipe.equipment or [])
    return tools or ["stovetop", "pan"]


def _eligible(store, diet=None, ten_minute_only=False, banned_ids=None, equipment=None):
    banned_ids = set(banned_ids or [])
    have = set(equipment) if equipment else None
    ids = shoppable_recipe_ids(store, ten_minute_only=ten_minute_only)
    recipes = []
    for rid in sorted(ids):
        if rid in banned_ids:
            continue
        recipe = Recipe.query.filter_by(id=rid).one()
        if diet and diet not in ("All", "Flexitarisch"):
            if diet not in (recipe.diets or []):
                continue
        if have is not None:
            needed = set(_recipe_equipment(recipe))
            if not needed.issubset(have):
                continue
        recipes.append(recipe)
    return recipes


def _by_slot(recipes):
    grouped = {slot: [r for r in recipes if r.slot == slot] for slot in SLOTS}
    return grouped


def _solve_assignment(
    by_slot,
    evals,
    days,
    budget,
    target_calories,
    target_protein,
    max_uses,
    enforce_budget,
    enforce_macros,
    locked=None,
    forbidden=None,
    forbid_adjacent=False,
):
    import pulp

    locked = locked or {}
    forbidden = forbidden or {}
    prob = pulp.LpProblem("kitchen_os_match", pulp.LpMinimize)
    x = {}

    for d in range(days):
        for slot in SLOTS:
            for recipe in by_slot[slot]:
                rid = recipe.id
                if (d, slot) in locked and rid != locked[(d, slot)]:
                    continue
                if rid in forbidden.get((d, slot), set()):
                    continue
                safe = rid.replace("-", "_")
                x[(d, slot, rid)] = pulp.LpVariable(
                    f"x_{d}_{SLOTS.index(slot)}_{safe}",
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
        extra = pulp.LpVariable(f"extra_{rid.replace('-', '_')}", lowBound=0)
        prob += extra >= pulp.lpSum(vars_r) - 1
        repeat_penalties.append(extra)

    if forbid_adjacent:
        for d in range(days - 1):
            for slot in SLOTS:
                for rid in recipe_ids:
                    a = x.get((d, slot, rid))
                    b = x.get((d + 1, slot, rid))
                    if a is not None and b is not None:
                        prob += a + b <= 1

    week_cost = pulp.lpSum(var * evals[rid]["cost"] for (d, slot, rid), var in x.items())
    if enforce_budget:
        prob += week_cost <= float(budget)

    cal_dev = []
    prot_dev = []
    for d in range(days):
        c_d = pulp.lpSum(
            var * evals[rid]["calories"]
            for (dd, slot, rid), var in x.items()
            if dd == d
        )
        p_d = pulp.lpSum(
            var * evals[rid]["protein"]
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

    deal_bonus = pulp.lpSum(var * evals[rid]["deals"] for (d, slot, rid), var in x.items())
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
                if r.id not in forbidden.get((d, slot), set())
            ]
            if not candidates:
                return None
            prev = picks.get((d - 1, slot))
            candidates = sorted(
                candidates,
                key=lambda r: (usage.get(r.id, 0), 1 if r.id == prev else 0, r.id),
            )
            rid = candidates[0].id
            picks[(d, slot)] = rid
            usage[rid] = usage.get(rid, 0) + 1
    return picks


def _scale(recipe, portions):
    base = max(1, int(recipe.servings or 2))
    portions = max(1, int(portions or 1))
    return portions / base


def _meal_payload(recipe, store, week, locked=False, portions=1):
    factor = _scale(recipe, portions)
    substitutes = []
    lines = []
    for line in recipe.lines:
        info = resolve_ingredient(line.ingredient_id, store, week)
        if info["is_substitute"]:
            substitutes.append({
                "ingredient_id": line.ingredient_id,
                "sku_name": info["sku_name"],
            })
        lines.append({
            "ingredient_id": line.ingredient_id,
            "quantity": round(line.quantity * factor, 2),
            "unit": line.unit,
            "sku_id": info["sku_id"],
            "sku_name": info["sku_name"],
            "is_substitute": info["is_substitute"],
            "is_deal": info["is_deal"],
            "deal_badge": info["deal_badge"],
        })
    return {
        "slot": recipe.slot,
        "recipe_id": recipe.id,
        "title": recipe.title,
        "cuisine": recipe.cuisine,
        "locale": recipe.locale,
        "active_time_minutes": recipe.active_time_minutes,
        "ten_minute": ten_minute_lane(recipe),
        "macros": {
            "calories": int(round(recipe.calories * factor)),
            "protein": int(round(recipe.protein * factor)),
            "carbs": int(round(recipe.carbs * factor)),
            "fat": int(round(recipe.fat * factor)),
            "fiber": int(round(recipe.fiber * factor)),
        },
        "steps": recipe.steps or [],
        "locked": locked,
        "substitutes": substitutes,
        "lines": lines,
    }


def match_week(
    store,
    week,
    days=7,
    budget=80,
    target_calories=2000,
    target_protein=120,
    diet=None,
    pantry=None,
    ten_minute_only=False,
    locked=None,
    forbidden=None,
    banned_ids=None,
    equipment=None,
    portions=1,
):
    if store not in STORES:
        raise MatchError("unknown_store")
    days = int(days)
    portions = max(1, int(portions or 1))
    locked = locked or {}
    forbidden = forbidden or {}
    recipes = _eligible(
        store,
        diet=diet,
        ten_minute_only=ten_minute_only,
        banned_ids=banned_ids,
        equipment=equipment,
    )
    by_slot = _by_slot(recipes)
    for slot in SLOTS:
        if not by_slot[slot]:
            raise MatchError("no_candidates", f"no shoppable recipes for {slot}")

    evals = {}
    for recipe in recipes:
        factor = _scale(recipe, portions)
        cost, deals = recipe_approx_cost(recipe, store, week)
        evals[recipe.id] = {
            "cost": cost * factor,
            "deals": deals,
            "calories": recipe.calories * factor,
            "protein": recipe.protein * factor,
        }

    short_slots = [slot for slot in SLOTS if len(by_slot[slot]) < days]
    attempts = [
        (1, True, True, False, None),
        (1, False, True, False, "budget"),
        (1, False, False, False, "macros"),
        (2, False, False, True, "variety"),
    ]
    relaxations = []
    picks = None
    for i, (max_uses, enforce_budget, enforce_macros, forbid_adj, tag) in enumerate(attempts):
        if i > 0 and tag and tag not in relaxations:
            relaxations.append(tag)
        picks = _solve_assignment(
            by_slot,
            evals,
            days,
            budget,
            target_calories,
            target_protein,
            max_uses,
            enforce_budget,
            enforce_macros,
            locked=locked,
            forbidden=forbidden,
            forbid_adjacent=forbid_adj,
        )
        if picks is not None:
            break
    if picks is None:
        picks = _greedy_fill(by_slot, days, locked=locked, forbidden=forbidden)
        for extra in ("variety", "budget", "macros"):
            if extra not in relaxations:
                relaxations.append(extra)
    if short_slots and "catalog_short" not in relaxations:
        relaxations.append("catalog_short")
    if picks is None:
        raise MatchError("unsolvable")

    by_id = {r.id: r for r in recipes}
    days_plan = []
    recipe_ids = []
    total_cals = total_prot = total_carbs = total_fat = 0
    for d in range(days):
        meals = []
        day_cals = day_prot = 0
        for slot in SLOTS:
            rid = picks[(d, slot)]
            recipe = by_id[rid]
            meal = _meal_payload(recipe, store, week, locked=(d, slot) in locked, portions=portions)
            meals.append(meal)
            recipe_ids.append(rid)
            day_cals += meal["macros"]["calories"]
            day_prot += meal["macros"]["protein"]
            total_carbs += meal["macros"]["carbs"]
            total_fat += meal["macros"]["fat"]
        total_cals += day_cals
        total_prot += day_prot
        days_plan.append({
            "day_index": d,
            "day_name": DAY_NAMES[d % 7],
            "calories": day_cals,
            "protein": day_prot,
            "meals": meals,
        })

    shopping = aggregate_ingredients(recipe_ids, store, week, pantry=pantry, portions=portions)
    total_cost = shopping["pack_cost"]
    return {
        "store": store,
        "week": week,
        "days": days,
        "budget": float(budget),
        "diet": diet,
        "ten_minute": bool(ten_minute_only),
        "target_calories": int(target_calories),
        "target_protein": int(target_protein),
        "relaxations": relaxations,
        "stale": shopping["stale"],
        "total_cost": total_cost,
        "regular_cost": shopping["regular_cost"],
        "deal_savings": shopping["deal_savings"],
        "pantry_savings": shopping["pantry_savings"],
        "over_budget": total_cost > float(budget),
        "daily_avg": {
            "calories": round(total_cals / days),
            "protein": round(total_prot / days),
            "carbs": round(total_carbs / days),
            "fat": round(total_fat / days),
        },
        "days_plan": days_plan,
        "shopping_list": {
            "to_buy": shopping["to_buy"],
            "already_at_home": shopping["already_at_home"],
            "pack_cost": shopping["pack_cost"],
        },
        "pantry": list(pantry or []),
        "recipe_ids": recipe_ids,
        "portions": portions,
        "equipment": list(equipment or []),
    }


def swap_slot(match, day_index, slot):
    locked = {}
    forbidden = {}
    current = None
    for day in match["days_plan"]:
        d = day["day_index"]
        for meal in day["meals"]:
            key = (d, meal["slot"])
            if d == day_index and meal["slot"] == slot:
                current = meal["recipe_id"]
                forbidden[key] = {meal["recipe_id"]}
            else:
                locked[key] = meal["recipe_id"]
    if current is None:
        raise MatchError("unknown_slot")
    try:
        nxt = match_week(
            store=match["store"],
            week=match["week"],
            days=match["days"],
            budget=match["budget"],
            target_calories=match["target_calories"],
            target_protein=match["target_protein"],
            diet=match.get("diet"),
            pantry=match.get("pantry"),
            ten_minute_only=match.get("ten_minute") or False,
            locked=locked,
            forbidden=forbidden,
            equipment=match.get("equipment"),
            portions=match.get("portions") or 1,
        )
    except MatchError as exc:
        raise MatchError("no_swap") from exc
    new_id = nxt["days_plan"][day_index]["meals"][list(SLOTS).index(slot)]["recipe_id"]
    if new_id == current:
        raise MatchError("no_swap")
    return nxt
