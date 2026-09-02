from pathlib import Path

from backend.extensions import db
from backend.kitchen.import_recipes import import_from_path, import_recipe_list
from backend.kitchen.models import Ingredient, Recipe
from backend.kitchen.shoppable import is_shoppable, shoppable_recipe_ids


RECIPES_FILE = Path(__file__).resolve().parents[1] / "recipes.txt"

SAMPLE = [
    {
        "id": "imp-hafer-test",
        "title": "Test-Hafer",
        "slot": "Frühstück",
        "active_time_minutes": 6,
        "servings": 2,
        "cuisine": "german",
        "steps": ["Hafer mit Milch aufkochen."],
        "lines": [
            {"ingredient_id": "oats", "quantity": 80, "unit": "g"},
            {"ingredient_id": "milk", "quantity": 200, "unit": "ml"},
            {"ingredient_id": "banana", "quantity": 120, "unit": "g"},
        ],
        "equipment": ["saucepan", "stovetop"],
        "calories": 300,
        "protein": 10,
        "carbs": 50,
        "fat": 8,
    }
]


def test_import_creates_shelf_and_publishes(app):
    with app.app_context():
        result = import_recipe_list(SAMPLE, publish_if_mapped=True)
        assert result["created"] == 1
        recipe = db.session.get(Recipe, "imp-hafer-test")
        assert recipe is not None
        assert recipe.status == "published"
        banana = db.session.get(Ingredient, "banana")
        assert banana is not None
        assert any(a.get("name") == "Banane" for a in (banana.aliases or []))
        assert is_shoppable("imp-hafer-test", "lidl")
        assert is_shoppable("imp-hafer-test", "marktkauf")


def test_import_is_idempotent(app):
    with app.app_context():
        first = import_recipe_list(SAMPLE, publish_if_mapped=True)
        second = import_recipe_list(SAMPLE, publish_if_mapped=True)
        assert first["created"] == 1
        assert second["created"] == 0
        assert second["skipped"] == 1
        assert Recipe.query.filter_by(id="imp-hafer-test").count() == 1


def test_import_recipes_file_fills_week_slots(app):
    with app.app_context():
        assert RECIPES_FILE.is_file()
        result = import_from_path(RECIPES_FILE)
        assert result["created"] >= 80
        published = Recipe.query.filter_by(status="published").count()
        assert published >= 80
        breakfast = shoppable_recipe_ids("lidl", slot="Frühstück")
        lunch = shoppable_recipe_ids("lidl", slot="Mittagessen")
        dinner = shoppable_recipe_ids("lidl", slot="Abendessen")
        assert len(breakfast) >= 20
        assert len(lunch) >= 20
        assert len(dinner) >= 20
