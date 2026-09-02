from collections import defaultdict
from math import ceil

from backend.algorithm import get_ingredient_pricing, nice_quantity, pack_info

AISLE_ORDER = [
    "Obst & Gemüse",
    "Kühlregal & Molkerei",
    "Kühlregal & Tiefkühl",
    "Fleisch, Fisch & Tofu",
    "Vorratskammer & Trocken",
    "Sonstiges",
]


def packs_needed(quantity, pack_size):
    if quantity <= 0 or pack_size <= 0:
        return 0
    return int(ceil(quantity / pack_size))


def _unit_factor(unit, pack_size):
    if unit == "Stück":
        return pack_size
    return pack_size / 100.0


def build_shopping_list(days_plan, store):
    aggregated = defaultdict(lambda: {
        "quantity": 0.0,
        "unit": "g",
        "is_deal": False,
        "deal_badge": None,
        "in_pantry": False,
        "aisle": "Sonstiges",
        "effective_price": None,
        "regular_price": None,
    })

    for day in days_plan:
        for meal in day.get("meals", []):
            for ing in meal.get("ingredients", []):
                key = ing["name"]
                item = aggregated[key]
                item["quantity"] += ing.get("quantity", 0)
                item["unit"] = ing.get("unit") or item["unit"]
                item["aisle"] = ing.get("aisle") or item["aisle"]
                if ing.get("is_deal"):
                    item["is_deal"] = True
                    item["deal_badge"] = ing.get("deal_badge")
                if ing.get("in_pantry"):
                    item["in_pantry"] = True
                if ing.get("effective_price") is not None:
                    item["effective_price"] = ing["effective_price"]
                if ing.get("regular_price") is not None:
                    item["regular_price"] = ing["regular_price"]

    to_buy_by_aisle = defaultdict(list)
    already_at_home = []
    pack_cost = 0.0

    for name, data in aggregated.items():
        size, unit, aisle = pack_info(name)
        aisle = data["aisle"] or aisle
        unit = data["unit"] or unit
        packs = 0 if data["in_pantry"] else packs_needed(data["quantity"], size)

        eff_price = data["effective_price"]
        if eff_price is None:
            eff_price, reg_price, is_deal, badge, _ = get_ingredient_pricing(name, store)
            if data["regular_price"] is None:
                data["regular_price"] = reg_price
            if is_deal:
                data["is_deal"] = True
                data["deal_badge"] = data["deal_badge"] or badge
        else:
            reg_price = data["regular_price"]

        cost = 0.0
        if packs and eff_price is not None and data["regular_price"] is not None:
            cost = round(packs * _unit_factor(unit, size) * eff_price, 2)
            pack_cost += cost

        row = {
            "name": name,
            "quantity": nice_quantity(data["quantity"], unit),
            "unit": unit,
            "packs": packs,
            "pack_size": size,
            "pack_unit": unit,
            "is_deal": data["is_deal"],
            "deal_badge": data["deal_badge"],
            "cost": cost,
            "aisle": aisle,
            "in_pantry": data["in_pantry"],
        }

        if data["in_pantry"]:
            already_at_home.append(row)
        else:
            to_buy_by_aisle[aisle].append(row)

    ordered = []
    seen = set()
    for aisle in AISLE_ORDER:
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
    return {
        "to_buy": ordered,
        "already_at_home": already_at_home,
        "pack_cost": round(pack_cost, 2),
    }
