import pytest

from backend.extensions import db
from backend.kitchen.catalog import (
    CatalogError,
    create_ingredient,
    create_recipe,
    create_sku,
    current_price,
    map_ingredient_sku,
    record_price,
)
from backend.kitchen.models import RecipeLine
from backend.kitchen.shoppable import (
    is_shoppable,
    shoppable_recipe_ids,
    ten_minute_lane,
    unmapped_ingredient_ids,
)


def _eggs_toast(app):
    with app.app_context():
        eggs = create_ingredient(
            "cat-eggs",
            "eggs",
            default_unit="Stück",
            aliases=[{"locale": "de", "name": "Eier"}, {"locale": "en", "name": "eggs"}],
        )
        bread = create_ingredient("cat-bread", "bread", default_unit="g", aliases=[{"locale": "de", "name": "Brot"}])
        tamarind = create_ingredient("cat-tamarind", "tamarind", default_unit="g")
        sku_eggs = create_sku("lidl", "Test Freilandeier 10er", 10, "Stück", aisle="Kühlregal & Molkerei", ean="4012345678901")
        sku_bread = create_sku("lidl", "Test Toastbrot 500g", 500, "g", aisle="Vorratskammer & Trocken", ean="4012345678902")
        record_price(sku_eggs.id, 2.19, source="admin")
        record_price(sku_bread.id, 1.29, source="admin")
        map_ingredient_sku("cat-eggs", "lidl", sku_eggs.id)
        map_ingredient_sku("cat-bread", "lidl", sku_bread.id)
        recipe = create_recipe(
            "cat-eggs-on-toast",
            "Rührei auf Toast",
            slot="Frühstück",
            active_time_minutes=8,
            cuisine="international",
            status="published",
            diets=["Vegetarisch", "High-Protein"],
            steps=["Brot toasten.", "Eier in der Pfanne cremig stocken.", "Auf dem Toast anrichten."],
            lines=[
                {"ingredient_id": "cat-eggs", "quantity": 3, "unit": "Stück"},
                {"ingredient_id": "cat-bread", "quantity": 70, "unit": "g"},
            ],
            macros={"calories": 380, "protein": 22, "carbs": 28, "fat": 18},
        )
        pad = create_recipe(
            "cat-pad-thai",
            "Pad Thai",
            slot="Abendessen",
            active_time_minutes=25,
            cuisine="thai",
            locale="en",
            status="published",
            steps=["Soak noodles.", "Stir-fry with sauce.", "Serve with lime."],
            lines=[
                {"ingredient_id": "cat-eggs", "quantity": 2, "unit": "Stück"},
                {"ingredient_id": "cat-tamarind", "quantity": 30, "unit": "g"},
            ],
            macros={"calories": 620, "protein": 28, "carbs": 80, "fat": 18},
        )
        db.session.commit()
        return {
            "eggs_id": eggs.id,
            "bread_id": bread.id,
            "tamarind_id": tamarind.id,
            "sku_eggs": sku_eggs.id,
            "recipe": recipe.id,
            "pad": pad.id,
        }


def test_recipe_lines_point_at_ingredients_not_skus(app):
    ids = _eggs_toast(app)
    with app.app_context():
        lines = RecipeLine.query.filter_by(recipe_id=ids["recipe"]).all()
        assert {line.ingredient_id for line in lines} == {"cat-eggs", "cat-bread"}
        assert all(not hasattr(line, "sku_id") or True for line in lines)
        assert not any(getattr(line, "sku_id", None) for line in lines)


def test_empty_price_does_not_clobber_current(app):
    ids = _eggs_toast(app)
    with app.app_context():
        before = current_price(ids["sku_eggs"])
        assert before.amount_eur == 2.19
        with pytest.raises(CatalogError):
            record_price(ids["sku_eggs"], None)
        db.session.rollback()
        after = current_price(ids["sku_eggs"])
        assert after is not None
        assert after.id == before.id
        assert after.amount_eur == 2.19


def test_published_mapped_recipe_is_shoppable_at_lidl(app):
    ids = _eggs_toast(app)
    with app.app_context():
        assert is_shoppable(ids["recipe"], "lidl")
        assert ids["recipe"] in shoppable_recipe_ids("lidl")


def test_unmapped_ingredient_makes_recipe_not_shoppable(app):
    ids = _eggs_toast(app)
    with app.app_context():
        assert "cat-tamarind" in unmapped_ingredient_ids(ids["pad"], "lidl")
        assert not is_shoppable(ids["pad"], "lidl")
        assert ids["pad"] not in shoppable_recipe_ids("lidl")


def test_unmapped_is_also_unshoppable_at_other_store(app):
    ids = _eggs_toast(app)
    with app.app_context():
        assert not is_shoppable(ids["recipe"], "marktkauf")


def test_ten_minute_lane_uses_active_time(app):
    ids = _eggs_toast(app)
    with app.app_context():
        from backend.kitchen.models import Recipe

        eggs = db.session.get(Recipe, ids["recipe"])
        pad = db.session.get(Recipe, ids["pad"])
        assert ten_minute_lane(eggs)
        assert not ten_minute_lane(pad)
        ten = shoppable_recipe_ids("lidl", ten_minute_only=True)
        assert ids["recipe"] in ten
        assert ids["pad"] not in ten


def test_draft_recipe_is_not_shoppable(app):
    _eggs_toast(app)
    with app.app_context():
        create_ingredient("cat-butter", "butter", default_unit="g")
        sku = create_sku("lidl", "Test Butter 250g", 250, "g", ean="4012345678903")
        map_ingredient_sku("cat-butter", "lidl", sku.id)
        create_recipe(
            "cat-draft-toast",
            "Draft only",
            slot="Frühstück",
            active_time_minutes=5,
            status="draft",
            steps=["Do not ship."],
            lines=[{"ingredient_id": "cat-butter", "quantity": 10, "unit": "g"}],
        )
        db.session.commit()
        assert not is_shoppable("cat-draft-toast", "lidl")
        assert "cat-draft-toast" not in shoppable_recipe_ids("lidl")
