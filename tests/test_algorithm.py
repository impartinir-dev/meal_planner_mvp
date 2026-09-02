from backend.algorithm import evaluate_recipe, generate_meal_plan, swap_single_meal, RECIPES


def test_pantry_zeros_cost_for_that_ingredient():
    r = next(r for r in RECIPES if r["id"] == "rec_01")
    without = evaluate_recipe(r, "Lidl", [])
    with_pantry = evaluate_recipe(r, "Lidl", ["Haferflocken"])
    assert with_pantry["cost"] < without["cost"]
    assert with_pantry["pantry_savings"] > 0
    oats = next(i for i in with_pantry["ingredients_detail"] if i["name"] == "Haferflocken")
    assert oats["in_pantry"] is True
    assert oats["item_cost"] == 0


def test_portions_scale_cost_and_quantities():
    r = next(r for r in RECIPES if r["id"] == "rec_01")
    one = evaluate_recipe(r, "Lidl", [], portions=1)
    two = evaluate_recipe(r, "Lidl", [], portions=2)
    assert abs(two["cost"] - 2 * one["cost"]) < 0.02
    oats1 = next(i for i in one["ingredients_detail"] if i["name"] == "Haferflocken")
    oats2 = next(i for i in two["ingredients_detail"] if i["name"] == "Haferflocken")
    assert oats2["quantity"] == 2 * oats1["quantity"]


def test_gram_quantities_are_whole_numbers_after_scaling():
    r = next(r for r in RECIPES if r["id"] == "rec_01")
    scaled = dict(r)
    scaled["ingredients"] = {k: v * (2200 / 1550) for k, v in r["ingredients"].items()}
    ev = evaluate_recipe(scaled, "Lidl", [])
    oats = next(i for i in ev["ingredients_detail"] if i["name"] == "Haferflocken")
    assert oats["quantity"] == int(oats["quantity"])
    assert oats["quantity"] == round(80 * 2200 / 1550)


def test_unknown_ingredient_does_not_silently_use_0_40():
    r = {
        "id": "x",
        "name": "X",
        "category": "Frühstück",
        "ingredients": {"Unobtainium": 100},
        "macros": {"calories": 1, "protein": 1, "carbs": 1, "fat": 1},
        "instructions": "",
        "diets": ["All"],
    }
    ev = evaluate_recipe(r, "Lidl", [])
    missing = ev["ingredients_detail"][0]
    assert missing.get("price_missing") is True


def test_macro_targets_change_the_plan():
    low = generate_meal_plan("Lidl", "All", 80, 5, 1600, 90, pantry=[], portions=1)
    high = generate_meal_plan("Lidl", "All", 80, 5, 2600, 160, pantry=[], portions=1)
    assert (
        low["daily_avg"]["calories"] != high["daily_avg"]["calories"]
        or low["daily_avg"]["protein"] != high["daily_avg"]["protein"]
    )
    assert abs(low["daily_avg"]["calories"] - 1600) < abs(low["daily_avg"]["calories"] - 2600)


def test_vegan_week_is_not_the_same_day_seven_times():
    plan = generate_meal_plan("REWE", "Vegan", 60, 7, 2000, 100, pantry=[], portions=1)
    signatures = [tuple(m["id"] for m in d["meals"]) for d in plan["days_plan"]]
    assert len(set(signatures)) >= 5


def test_budget_flag_when_impossible():
    plan = generate_meal_plan("Lidl", "High-Protein", 15, 7, 2200, 140, pantry=[], portions=1)
    assert plan["status"] == "success"
    assert plan["over_budget"] is True or "budget" in plan["relaxations"]


def test_exclude_peanut_skips_peanut_butter():
    plan = generate_meal_plan(
        "Lidl", "All", 80, 5, 2000, 120, pantry=[], portions=1, exclude=["Erdnuss"]
    )
    for day in plan["days_plan"]:
        for meal in day["meals"]:
            names = [i["name"] for i in meal["ingredients"]]
            assert "Erdnussbutter" not in names


def test_week_starts_today():
    from datetime import date
    from backend.algorithm import DAYS_NAMES

    today = DAYS_NAMES[date.today().weekday()]
    plan = generate_meal_plan("Lidl", "All", 70, 5, 2000, 120)
    assert plan["days_plan"][0]["day_name"] == today


def test_locked_meal_cannot_be_swapped():
    plan = generate_meal_plan("Lidl", "All", 70, 5, 2000, 120)
    plan["days_plan"][0]["meals"][1]["locked"] = True
    current_id = plan["days_plan"][0]["meals"][1]["id"]
    assert swap_single_meal(plan, 0, "Mittagessen", current_id) is None


def test_diet_all_does_not_require_tag_all_only():
    plan = generate_meal_plan("Lidl", "All", 70, 5, 2000, 120)
    assert len(plan["days_plan"]) == 5
    assert all(len(d["meals"]) == 3 for d in plan["days_plan"])


def test_swap_changes_that_slot_and_rebuilds_totals():
    plan = generate_meal_plan("Lidl", "All", 70, 5, 2000, 120, pantry=["Olivenöl"], portions=1)
    day0 = plan["days_plan"][0]
    old_id = day0["meals"][1]["id"]
    new_plan = swap_single_meal(plan, 0, "Mittagessen", old_id)
    assert new_plan is not None
    assert new_plan["days_plan"][0]["meals"][1]["id"] != old_id
    assert new_plan["days_plan"][0]["meals"][0]["id"] == day0["meals"][0]["id"]
    assert "to_buy" in new_plan["shopping_list"]
    assert new_plan["days_plan"][0]["calories"] == sum(
        m["macros"]["calories"] for m in new_plan["days_plan"][0]["meals"]
    )
