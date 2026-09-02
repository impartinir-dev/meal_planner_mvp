import pytest

from backend.extensions import db
from backend.kitchen.catalog import record_price
from backend.kitchen.matcher import MatchError, match_week, swap_slot
from backend.kitchen.models import FrozenPack, Sku
from backend.kitchen.pack import freeze_pack
from backend.kitchen.seed import seed_owned_catalog
from backend.kitchen.shopping import aggregate_ingredients


def _seed(app):
    with app.app_context():
        seed_owned_catalog()


def test_match_never_includes_unmapped_pad_thai(app):
    _seed(app)
    with app.app_context():
        result = match_week("lidl", "2026-W36", days=5, budget=80, target_calories=1200, target_protein=50)
        assert "pad-thai" not in result["recipe_ids"]
        assert len(result["days_plan"]) == 5
        assert all(len(day["meals"]) == 3 for day in result["days_plan"])
        assert result["shopping_list"]["pack_cost"] > 0


def test_match_one_store_marktkauf(app):
    _seed(app)
    with app.app_context():
        result = match_week("marktkauf", "2026-W36", days=5, budget=90, target_calories=1200, target_protein=40)
        assert result["store"] == "marktkauf"
        assert "eggs-on-toast" not in result["recipe_ids"]
        assert "pad-thai" not in result["recipe_ids"]
        assert "oat-bowl" in result["recipe_ids"]


def test_ten_minute_without_lunch_fails(app):
    _seed(app)
    with app.app_context():
        with pytest.raises(MatchError) as err:
            match_week("lidl", "2026-W36", days=3, ten_minute_only=True)
        assert err.value.code == "no_candidates"


def test_pantry_partial_rice_still_buys_a_pack(app):
    _seed(app)
    with app.app_context():
        shopping = aggregate_ingredients(
            ["soy-fried-rice"],
            "lidl",
            "2026-W36",
            pantry=[{"ingredient_id": "rice", "quantity": 50, "unit": "g"}],
            portions=2,
        )
        rice = next(
            item
            for group in shopping["to_buy"]
            for item in group["items"]
            if item["ingredient_id"] == "rice"
        )
        assert rice["net_quantity"] == 100
        assert rice["packs"] == 1
        assert rice["cost"] == 1.49


def test_pantry_full_rice_drops_line(app):
    _seed(app)
    with app.app_context():
        shopping = aggregate_ingredients(
            ["soy-fried-rice"],
            "lidl",
            "2026-W36",
            pantry=[{"ingredient_id": "rice", "quantity": 200, "unit": "g"}],
            portions=2,
        )
        bought = [item["ingredient_id"] for group in shopping["to_buy"] for item in group["items"]]
        assert "rice" not in bought
        home = [item["ingredient_id"] for item in shopping["already_at_home"]]
        assert "rice" in home
        assert shopping["pantry_savings"] > 0


def test_w36_uses_egg_offer(app):
    _seed(app)
    with app.app_context():
        shopping = aggregate_ingredients(["savory-soy-eggs"], "lidl", "2026-W36", portions=2)
        eggs = next(
            item
            for group in shopping["to_buy"]
            for item in group["items"]
            if item["ingredient_id"] == "eggs"
        )
        assert eggs["is_deal"]
        assert eggs["deal_badge"] == "Prospekt-Knaller"
        assert eggs["cost"] == 1.79


def test_swap_breakfast_changes_recipe(app):
    _seed(app)
    with app.app_context():
        result = match_week("lidl", "2026-W36", days=5, budget=80, target_calories=1200, target_protein=50)
        original = result["days_plan"][0]["meals"][0]["recipe_id"]
        assert result["days_plan"][0]["meals"][0]["slot"] == "Frühstück"
        nxt = swap_slot(result, 0, "Frühstück")
        assert nxt["days_plan"][0]["meals"][0]["recipe_id"] != original


def test_swap_only_dinner_exhausts(app):
    _seed(app)
    with app.app_context():
        result = match_week("lidl", "2026-W36", days=5, budget=80, target_calories=1200, target_protein=50)
        with pytest.raises(MatchError) as err:
            swap_slot(result, 0, "Abendessen")
        assert err.value.code == "no_swap"


def test_frozen_pack_does_not_change_when_price_moves(app):
    _seed(app)
    with app.app_context():
        result = match_week("lidl", "2026-W36", days=5, budget=80, target_calories=1200, target_protein=50)
        row = freeze_pack(result)
        db.session.commit()
        pack_id = row.id
        frozen_cost = row.match_json["total_cost"]
        eggs = Sku.query.filter_by(ean="400000000001").one()
        record_price(eggs.id, 9.99)
        db.session.commit()
        stored = db.session.get(FrozenPack, pack_id)
        assert stored.match_json["total_cost"] == frozen_cost
        assert stored.revision == 1
        assert "Rührei" in stored.markdown or "Haferflocken" in stored.markdown
        again = freeze_pack(result)
        db.session.commit()
        assert again.revision == 2


def test_breakfast_alternates_when_catalog_is_short(app):
    _seed(app)
    with app.app_context():
        result = match_week("lidl", "2026-W36", days=5, budget=80, target_calories=1200, target_protein=50)
        breakfasts = [d["meals"][0]["recipe_id"] for d in result["days_plan"]]
        assert len(set(breakfasts)) >= 2
        for i in range(1, 5):
            if breakfasts[i] == breakfasts[i - 1]:
                # only allowed if that slot has a single recipe
                assert False, "adjacent breakfast repeat"
        lunches = [d["meals"][1]["recipe_id"] for d in result["days_plan"]]
        assert "catalog_short" in result["relaxations"]
        assert len(set(lunches)) == 1


def test_match_api_and_pack_roundtrip(client, app):
    with app.app_context():
        seed_owned_catalog()
    client.post("/api/auth/login", json={"email": "admin@test.local", "password": "testdevpass"})
    r = client.post("/api/kitchen/match", json={
        "store": "lidl",
        "week": "2026-W36",
        "days": 5,
        "budget": 80,
        "target_calories": 1200,
        "target_protein": 50,
    })
    assert r.status_code == 200
    match = r.get_json()
    assert "pad-thai" not in match["recipe_ids"]
    packed = client.post("/api/kitchen/packs", json={"match": match})
    assert packed.status_code == 201
    pack_id = packed.get_json()["id"]
    got = client.get(f"/api/kitchen/packs/{pack_id}")
    assert got.status_code == 200
    assert got.get_json()["revision"] == 1
    assert got.get_json()["match"]["total_cost"] == match["total_cost"]
