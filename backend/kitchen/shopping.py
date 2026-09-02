from collections import defaultdict
from math import ceil

from backend.kitchen.constants import AISLES
from backend.kitchen.models import Recipe, RecipeLine
from backend.kitchen.resolve import resolve_ingredient


def packs_needed(quantity, pack_size):
    if quantity <= 0 or pack_size <= 0:
        return 0
    return int(ceil(quantity / pack_size))


def pantry_map(pantry):
    out = {}
    for item in pantry or []:
        if isinstance(item, str):
            out[item] = {"quantity": 10**9, "unit": None}
            continue
        iid = item.get("ingredient_id") or item.get("id")
        if not iid:
            continue
        out[iid] = {
            "quantity": float(item.get("quantity") or 0),
            "unit": item.get("unit"),
        }
    return out


def _needed_qty(line, yield_factor):
    return float(line.quantity) * float(yield_factor or 1.0)


def aggregate_ingredients(recipe_ids, store, week, pantry=None, portions=1):
    pantry = pantry_map(pantry)
    portions = max(1, int(portions or 1))
    totals = {}
    stale = False
    for recipe_id in recipe_ids:
        recipe = Recipe.query.filter_by(id=recipe_id).one()
        factor = portions / max(1, int(recipe.servings or 2))
        for line in RecipeLine.query.filter_by(recipe_id=recipe.id).order_by(RecipeLine.position):
            info = resolve_ingredient(line.ingredient_id, store, week)
            stale = stale or info["stale"]
            key = info["sku_id"]
            row = totals.get(key)
            if row is None:
                row = {
                    **info,
                    "quantity": 0.0,
                    "unit": line.unit,
                }
                totals[key] = row
            row["quantity"] += _needed_qty(line, info["yield_factor"]) * factor
            row["is_deal"] = row["is_deal"] or info["is_deal"]
            row["deal_badge"] = row["deal_badge"] or info["deal_badge"]
            row["is_substitute"] = row["is_substitute"] or info["is_substitute"]

    to_buy_by_aisle = defaultdict(list)
    already_at_home = []
    pack_cost = 0.0
    regular_cost = 0.0
    pantry_savings = 0.0

    for row in totals.values():
        iid = row["ingredient_id"]
        have = pantry.get(iid) or {"quantity": 0.0, "unit": None}
        deduct = 0.0
        if have["quantity"] and (have["unit"] in (None, row["unit"])):
            deduct = min(row["quantity"], have["quantity"])
        net = max(0.0, row["quantity"] - deduct)
        packs = packs_needed(net, row["pack_size"])
        packs_full = packs_needed(row["quantity"], row["pack_size"])
        cost = round(packs * row["amount_eur"], 2)
        full_cost = round(packs_full * row["amount_eur"], 2)
        pack_cost += cost
        regular_cost += round(packs * (row["regular_eur"] or row["amount_eur"]), 2)
        pantry_savings += round(full_cost - cost, 2)
        item = {
            "ingredient_id": iid,
            "name": row["sku_name"],
            "ingredient_name": row["ingredient_name"],
            "sku_id": row["sku_id"],
            "quantity": round(row["quantity"], 2),
            "net_quantity": round(net, 2),
            "unit": row["unit"],
            "packs": packs,
            "pack_size": row["pack_size"],
            "pack_unit": row["pack_unit"],
            "aisle": row["aisle"],
            "cost": cost,
            "is_deal": row["is_deal"],
            "deal_badge": row["deal_badge"],
            "is_substitute": row["is_substitute"],
            "in_pantry": packs == 0 and deduct > 0,
        }
        if item["in_pantry"]:
            already_at_home.append(item)
        else:
            to_buy_by_aisle[row["aisle"]].append(item)

    ordered = []
    seen = set()
    for aisle in AISLES:
        if aisle in to_buy_by_aisle:
            ordered.append({
                "aisle": aisle,
                "items": sorted(to_buy_by_aisle[aisle], key=lambda x: x["name"]),
            })
            seen.add(aisle)
    for aisle, items in sorted(to_buy_by_aisle.items()):
        if aisle not in seen:
            ordered.append({
                "aisle": aisle,
                "items": sorted(items, key=lambda x: x["name"]),
            })
    already_at_home.sort(key=lambda x: x["name"])
    deal_savings = round(max(0.0, regular_cost - pack_cost), 2)
    return {
        "to_buy": ordered,
        "already_at_home": already_at_home,
        "pack_cost": round(pack_cost, 2),
        "regular_cost": round(regular_cost, 2),
        "deal_savings": deal_savings,
        "pantry_savings": round(pantry_savings, 2),
        "stale": stale,
    }


def recipe_approx_cost(recipe, store, week):
    cost = 0.0
    deals = 0
    for line in recipe.lines:
        info = resolve_ingredient(line.ingredient_id, store, week)
        frac = _needed_qty(line, info["yield_factor"]) / info["pack_size"]
        cost += frac * info["amount_eur"]
        if info["is_deal"]:
            deals += 1
    return cost, deals
