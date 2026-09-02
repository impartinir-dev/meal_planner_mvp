from backend.extensions import db
from backend.kitchen.catalog import current_price
from backend.kitchen.constants import TEN_MINUTE_MAX
from backend.kitchen.models import IngredientSku, Recipe, RecipeLine


def ten_minute_lane(recipe):
    return recipe.active_time_minutes <= TEN_MINUTE_MAX


def mapping_for(ingredient_id, store):
    rows = IngredientSku.query.filter_by(ingredient_id=ingredient_id, store=store).all()
    if not rows:
        return None
    preferred = [row for row in rows if not row.is_substitute]
    return (preferred or rows)[0]


def unmapped_ingredient_ids(recipe_id, store):
    lines = RecipeLine.query.filter_by(recipe_id=recipe_id).all()
    missing = []
    for line in lines:
        mapped = mapping_for(line.ingredient_id, store)
        if mapped is None or current_price(mapped.sku_id) is None:
            missing.append(line.ingredient_id)
    return missing


def is_shoppable(recipe_id, store):
    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None or recipe.status != "published":
        return False
    return not unmapped_ingredient_ids(recipe_id, store)


def shoppable_recipe_ids(store, slot=None, ten_minute_only=False):
    q = Recipe.query.filter_by(status="published")
    if slot:
        q = q.filter_by(slot=slot)
    ids = []
    for recipe in q.all():
        if ten_minute_only and not ten_minute_lane(recipe):
            continue
        if is_shoppable(recipe.id, store):
            ids.append(recipe.id)
    return ids
