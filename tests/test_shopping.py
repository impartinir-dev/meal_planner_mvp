from backend.shopping import build_shopping_list, packs_needed


def test_oats_round_up_to_500g_packs():
    assert packs_needed(80, 500) == 1
    assert packs_needed(501, 500) == 2
    assert packs_needed(0, 500) == 0


def test_pantry_items_are_not_on_the_buy_list():
    days_plan = [{
        "meals": [{
            "ingredients": [
                {
                    "name": "Haferflocken",
                    "quantity": 80,
                    "unit": "g",
                    "is_deal": False,
                    "deal_badge": None,
                    "in_pantry": True,
                    "item_cost": 0.0,
                    "aisle": "Vorratskammer & Trocken",
                    "effective_price": 0.18,
                    "regular_price": 0.18,
                },
                {
                    "name": "Magerquark",
                    "quantity": 250,
                    "unit": "g",
                    "is_deal": True,
                    "deal_badge": "Lidl Plus Deal",
                    "in_pantry": False,
                    "item_cost": 0.95,
                    "aisle": "Kühlregal & Molkerei",
                    "effective_price": 0.38,
                    "regular_price": 0.55,
                },
            ]
        }]
    }]
    result = build_shopping_list(days_plan, "Lidl")
    buy_names = [i["name"] for a in result["to_buy"] for i in a["items"]]
    home_names = [i["name"] for i in result["already_at_home"]]
    assert "Haferflocken" not in buy_names
    assert "Haferflocken" in home_names
    assert "Magerquark" in buy_names


def test_shopping_quantities_are_whole_grams():
    days_plan = [{
        "meals": [{
            "ingredients": [{
                "name": "Reis",
                "quantity": 103.2258064516129,
                "unit": "g",
                "is_deal": False,
                "deal_badge": None,
                "in_pantry": False,
                "item_cost": 0.2,
                "aisle": "Vorratskammer & Trocken",
                "effective_price": 0.22,
                "regular_price": 0.22,
            }]
        }]
    }]
    result = build_shopping_list(days_plan, "Lidl")
    reis = result["to_buy"][0]["items"][0]
    assert reis["quantity"] == 103
    assert reis["quantity"] == int(reis["quantity"])
