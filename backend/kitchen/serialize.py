from backend.kitchen.constants import TEN_MINUTE_MAX
from backend.kitchen.models import Offer, PriceObservation, Recipe, Sku
from backend.kitchen.shoppable import is_shoppable, ten_minute_lane, unmapped_ingredient_ids


STORE_META = {
    "lidl": {"id": "lidl", "name": "Lidl", "badge": "Discounter", "logo_char": "L"},
    "marktkauf": {"id": "marktkauf", "name": "Marktkauf", "badge": "Supermarkt", "logo_char": "M"},
}


def live_store_ids():
    rows = (
        Sku.query.join(PriceObservation, PriceObservation.sku_id == Sku.id)
        .filter(PriceObservation.is_current.is_(True))
        .with_entities(Sku.store)
        .distinct()
        .all()
    )
    return [store for (store,) in rows if store in STORE_META]


def live_stores():
    ids = live_store_ids()
    return [STORE_META[sid] for sid in ("lidl", "marktkauf") if sid in ids]


def recipe_public(recipe, store=None):
    payload = {
        "id": recipe.id,
        "title": recipe.title,
        "cuisine": recipe.cuisine,
        "locale": recipe.locale,
        "slot": recipe.slot,
        "active_time_minutes": recipe.active_time_minutes,
        "ten_minute": ten_minute_lane(recipe),
        "servings": recipe.servings,
        "status": recipe.status,
        "diets": recipe.diets or [],
        "allergens": recipe.allergens or [],
        "macros": {
            "calories": recipe.calories,
            "protein": recipe.protein,
            "carbs": recipe.carbs,
            "fat": recipe.fat,
            "fiber": recipe.fiber,
        },
        "steps": recipe.steps or [],
        "lines": [
            {
                "ingredient_id": line.ingredient_id,
                "quantity": line.quantity,
                "unit": line.unit,
                "notes": line.notes,
            }
            for line in recipe.lines
        ],
    }
    if store:
        payload["shoppable"] = is_shoppable(recipe.id, store)
        payload["unmapped"] = unmapped_ingredient_ids(recipe.id, store)
    return payload


def sku_public(sku):
    obs = PriceObservation.query.filter_by(sku_id=sku.id, is_current=True).one_or_none()
    offer = Offer.query.filter_by(sku_id=sku.id, is_current=True).one_or_none()
    return {
        "id": sku.id,
        "store": sku.store,
        "name": sku.name,
        "brand": sku.brand,
        "ean": sku.ean,
        "pack_size": sku.pack_size,
        "pack_unit": sku.pack_unit,
        "aisle": sku.aisle,
        "price": None
        if obs is None
        else {
            "amount_eur": obs.amount_eur,
            "source": obs.source,
            "stale": obs.stale,
            "observed_at": obs.observed_at.isoformat() if obs.observed_at else None,
        },
        "offer": None
        if offer is None
        else {
            "week": offer.week,
            "offer_price": offer.offer_price,
            "regular_price": offer.regular_price,
            "badge": offer.badge,
        },
    }
