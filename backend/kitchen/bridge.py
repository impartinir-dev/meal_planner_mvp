from datetime import date

from backend.extensions import db
from backend.kitchen.matcher import MatchError, match_week, swap_slot
from backend.kitchen.models import Ingredient, Offer, Sku
from backend.kitchen.resolve import display_name
from backend.kitchen.serialize import STORE_META, live_stores
from backend.kitchen.shopping import recipe_approx_cost
from backend.models import CupboardItem


SLOT_ICONS = {
    "Frühstück": "sun",
    "Mittagessen": "utensils",
    "Abendessen": "moon",
}

STORE_ALIASES = {
    "lidl": "lidl",
    "marktkauf": "marktkauf",
    "Lidl": "lidl",
    "Marktkauf": "marktkauf",
}


def current_iso_week():
    year, week, _ = date.today().isocalendar()
    return f"{year}-W{week:02d}"


def normalize_store(store):
    if not store:
        return None
    if store in STORE_ALIASES:
        return STORE_ALIASES[store]
    lowered = str(store).strip().lower()
    return lowered if lowered in STORE_META else None


def active_week(store):
    iso = current_iso_week()
    weeks = [
        row.week
        for row in (
            Offer.query.join(Sku, Offer.sku_id == Sku.id)
            .filter(Sku.store == store, Offer.is_current.is_(True))
            .all()
        )
        if row.week
    ]
    if iso in weeks:
        return iso
    if weeks:
        return sorted(weeks)[-1]
    return iso


def find_ingredient_id(name):
    if not name:
        return None
    needle = str(name).strip().lower()
    for ing in Ingredient.query.all():
        if ing.id == needle or ing.canonical_name.lower() == needle:
            return ing.id
        for alias in ing.aliases or []:
            if str(alias.get("name") or "").strip().lower() == needle:
                return ing.id
    return None


def pantry_staples():
    items = []
    for ing in Ingredient.query.order_by(Ingredient.id).all():
        items.append({
            "name": display_name(ing),
            "icon": "circle",
            "hint": ing.canonical_name,
        })
    return items


def kitchen_ingredients():
    return [display_name(ing) for ing in Ingredient.query.order_by(Ingredient.id).all()]


def _pantry_entries(names, cupboard_rows):
    qty = {}
    for name in names or []:
        iid = find_ingredient_id(name) or (name if db.session.get(Ingredient, name) else None)
        if not iid:
            continue
        qty[iid] = {"ingredient_id": iid, "quantity": 10**9, "unit": None}
    for row in cupboard_rows or []:
        if (row.quantity or 0) <= 0:
            continue
        iid = find_ingredient_id(row.name)
        if not iid:
            continue
        current = qty.get(iid)
        if current is None or current["quantity"] >= 10**9:
            qty[iid] = {
                "ingredient_id": iid,
                "quantity": float(row.quantity),
                "unit": row.unit or None,
            }
        else:
            qty[iid]["quantity"] += float(row.quantity)
    return list(qty.values())


def _meal(kitchen_meal, store, week, status=None):
    from backend.kitchen.models import Recipe

    recipe = db.session.get(Recipe, kitchen_meal["recipe_id"])
    cost, _deals = recipe_approx_cost(recipe, store, week) if recipe else (0.0, 0)
    lines = []
    for line in kitchen_meal.get("lines") or []:
        lines.append({
            "name": line.get("sku_name") or line.get("ingredient_id"),
            "quantity": line.get("quantity") or 0,
            "unit": line.get("unit") or "g",
            "is_deal": bool(line.get("is_deal")),
            "deal_badge": line.get("deal_badge"),
            "in_pantry": False,
            "item_cost": 0,
            "aisle": "",
        })
    return {
        "id": kitchen_meal["recipe_id"],
        "name": kitchen_meal["title"],
        "category": kitchen_meal["slot"],
        "prep_time": f"{kitchen_meal['active_time_minutes']} Min",
        "lucide_icon": SLOT_ICONS.get(kitchen_meal["slot"], "utensils"),
        "cost": round(cost, 2),
        "regular_cost": round(cost, 2),
        "deal_savings": 0,
        "has_deal": any(line.get("is_deal") for line in kitchen_meal.get("lines") or []),
        "macros": kitchen_meal.get("macros") or {"calories": 0, "protein": 0, "carbs": 0, "fat": 0},
        "ingredients": lines,
        "instructions": kitchen_meal.get("steps") or [],
        "locked": bool(kitchen_meal.get("locked")),
        "status": status,
    }


def _shopping(kitchen):
    to_buy = []
    for group in kitchen.get("shopping_list", {}).get("to_buy") or []:
        items = []
        for item in group.get("items") or []:
            items.append({
                "name": item.get("name"),
                "quantity": item.get("net_quantity") if item.get("net_quantity") is not None else item.get("quantity"),
                "unit": item.get("unit"),
                "packs": item.get("packs") or 0,
                "pack_size": item.get("pack_size") or 0,
                "pack_unit": item.get("pack_unit") or item.get("unit"),
                "is_deal": bool(item.get("is_deal")),
                "deal_badge": item.get("deal_badge"),
                "cost": item.get("cost") or 0,
                "aisle": group.get("aisle"),
                "in_pantry": False,
            })
        to_buy.append({"aisle": group.get("aisle"), "items": items})
    already = []
    for item in kitchen.get("shopping_list", {}).get("already_at_home") or []:
        already.append({
            "name": item.get("name"),
            "quantity": item.get("quantity") or 0,
            "unit": item.get("unit"),
            "packs": 0,
            "pack_size": item.get("pack_size") or 0,
            "pack_unit": item.get("pack_unit") or item.get("unit"),
            "is_deal": False,
            "deal_badge": None,
            "cost": 0,
            "aisle": item.get("aisle") or "",
            "in_pantry": True,
        })
    return {
        "to_buy": to_buy,
        "already_at_home": already,
        "pack_cost": kitchen.get("shopping_list", {}).get("pack_cost") or kitchen.get("total_cost") or 0,
    }


def to_nutrimatch(kitchen, prefs, previous=None):
    store = kitchen["store"]
    week = kitchen["week"]
    prev_status = {}
    if previous:
        for day in previous.get("days_plan") or []:
            for meal in day.get("meals") or []:
                prev_status[(day["day_index"], meal.get("category"))] = meal.get("status")
    days_plan = []
    for day in kitchen["days_plan"]:
        meals = []
        day_cost = 0.0
        for meal in day["meals"]:
            status = prev_status.get((day["day_index"], meal["slot"]))
            mapped = _meal(meal, store, week, status=status)
            day_cost += mapped["cost"]
            meals.append(mapped)
        days_plan.append({
            "day_index": day["day_index"],
            "day_name": day["day_name"],
            "cost": round(day_cost, 2),
            "calories": day.get("calories") or 0,
            "protein": day.get("protein") or 0,
            "meals": meals,
        })
    shopping = _shopping(kitchen)
    total = shopping["pack_cost"]
    budget = float(prefs.get("budget") or kitchen.get("budget") or 0)
    display = STORE_META.get(store, {}).get("name", store)
    plan = {
        "status": "success",
        "store": display,
        "diet": prefs.get("diet") or kitchen.get("diet") or "All",
        "days": kitchen["days"],
        "budget": budget,
        "portions": prefs.get("portions") or 1,
        "target_calories": kitchen["target_calories"],
        "target_protein": kitchen["target_protein"],
        "deal_week": week,
        "total_cost": total,
        "regular_cost": kitchen.get("regular_cost") or total,
        "deal_savings": kitchen.get("deal_savings") or 0,
        "pantry_savings": kitchen.get("pantry_savings") or 0,
        "combined_savings": round(
            (kitchen.get("deal_savings") or 0) + (kitchen.get("pantry_savings") or 0),
            2,
        ),
        "budget_percent": min(100, round((total / budget) * 100)) if budget else 0,
        "over_budget": bool(kitchen.get("over_budget")),
        "relaxations": kitchen.get("relaxations") or [],
        "daily_avg": kitchen.get("daily_avg") or {"calories": 0, "protein": 0, "carbs": 0, "fat": 0},
        "days_plan": days_plan,
        "shopping_list": shopping,
        "pantry_items": list(prefs.get("pantry") or []),
        "exclude": list(prefs.get("exclude") or []),
        "members": list(prefs.get("members") or []),
        "banned_ids": list(prefs.get("banned_ids") or kitchen.get("banned_ids") or []),
        "recipe_cost": round(sum(d["cost"] for d in days_plan), 2),
        "checkout_cost": total,
        "_kitchen": kitchen,
    }
    return plan


def _locks_from_plan(plan):
    locked = {}
    for day in plan.get("days_plan") or []:
        for meal in day.get("meals") or []:
            if meal.get("locked"):
                locked[(day["day_index"], meal["category"])] = meal["id"]
    return locked


def generate_client_plan(prefs, user_id, banned_ids=None, locked=None):
    store = normalize_store(prefs["store"])
    if store is None:
        raise MatchError("unknown_store")
    live = {item["id"] for item in live_stores()}
    if store not in live:
        raise MatchError("unknown_store")
    cupboard = CupboardItem.query.filter_by(user_id=user_id).all()
    pantry = _pantry_entries(prefs.get("pantry"), cupboard)
    week = active_week(store)
    diet = prefs.get("diet")
    banned_ids = list(banned_ids or [])
    members = prefs.get("members") or []
    portions = max(1, int(prefs.get("portions") or len(members) or 1))
    if members:
        target_cal = sum(int(m.get("calories") or 0) for m in members)
        target_prot = sum(int(m.get("protein") or 0) for m in members)
    else:
        target_cal = int(prefs["calories"]) * portions
        target_prot = int(prefs["protein"]) * portions
    equipment = prefs.get("equipment")
    try:
        kitchen = match_week(
            store=store,
            week=week,
            days=prefs["days"],
            budget=prefs["budget"],
            target_calories=target_cal,
            target_protein=target_prot,
            diet=diet,
            pantry=pantry,
            locked=locked or {},
            banned_ids=banned_ids,
            equipment=equipment,
            portions=portions,
        )
    except MatchError as exc:
        if exc.code == "no_candidates" and diet not in (None, "All", "Flexitarisch"):
            kitchen = match_week(
                store=store,
                week=week,
                days=prefs["days"],
                budget=prefs["budget"],
                target_calories=target_cal,
                target_protein=target_prot,
                diet=None,
                pantry=pantry,
                locked=locked or {},
                banned_ids=banned_ids,
                equipment=equipment,
                portions=portions,
            )
            kitchen["relaxations"] = ["diet"] + list(kitchen.get("relaxations") or [])
        else:
            raise
    prefs_out = dict(prefs)
    prefs_out["store"] = store
    prefs_out["banned_ids"] = banned_ids
    return to_nutrimatch(kitchen, prefs_out)


def swap_client_plan(plan, prefs, day_index, category):
    kitchen = plan.get("_kitchen")
    if not kitchen:
        raise MatchError("no_swap")
    for day in plan.get("days_plan") or []:
        if day["day_index"] != day_index:
            continue
        for meal in day.get("meals") or []:
            if meal.get("category") == category and meal.get("locked"):
                raise MatchError("no_swap")
    nxt = swap_slot(kitchen, day_index, category)
    prefs_out = dict(prefs)
    return to_nutrimatch(nxt, prefs_out, previous=plan)
