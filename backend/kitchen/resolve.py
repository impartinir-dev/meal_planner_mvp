from datetime import datetime, timezone

from backend.extensions import db
from backend.kitchen.catalog import current_price
from backend.kitchen.models import Ingredient, Offer, Sku
from backend.kitchen.shoppable import mapping_for


class ResolveError(ValueError):
    pass


def _in_window(offer, now):
    if offer.valid_from and now < offer.valid_from:
        return False
    if offer.valid_to and now > offer.valid_to:
        return False
    return True


def current_offer(sku_id, week, now=None):
    now = now or datetime.now(timezone.utc)
    offer = Offer.query.filter_by(sku_id=sku_id, is_current=True).one_or_none()
    if offer is None:
        return None
    if offer.week and week and offer.week != week:
        return None
    if not _in_window(offer, now):
        return None
    return offer


def display_name(ingredient):
    for alias in ingredient.aliases or []:
        if alias.get("locale") == "de" and alias.get("name"):
            return alias["name"]
    return ingredient.canonical_name


def resolve_ingredient(ingredient_id, store, week):
    mapping = mapping_for(ingredient_id, store)
    if mapping is None:
        raise ResolveError(f"unmapped:{ingredient_id}")
    sku = db.session.get(Sku, mapping.sku_id)
    obs = current_price(sku.id)
    if obs is None:
        raise ResolveError(f"no_price:{ingredient_id}")
    offer = current_offer(sku.id, week)
    effective = offer.offer_price if offer is not None else obs.amount_eur
    regular = None
    if offer is not None:
        regular = offer.regular_price if offer.regular_price is not None else obs.amount_eur
    else:
        regular = obs.amount_eur
    ingredient = db.session.get(Ingredient, ingredient_id)
    return {
        "ingredient_id": ingredient_id,
        "ingredient_name": display_name(ingredient),
        "sku_id": sku.id,
        "sku_name": sku.name,
        "pack_size": sku.pack_size,
        "pack_unit": sku.pack_unit,
        "aisle": sku.aisle,
        "is_substitute": bool(mapping.is_substitute),
        "yield_factor": float(mapping.yield_factor or 1.0),
        "amount_eur": effective,
        "regular_eur": regular,
        "is_deal": offer is not None,
        "deal_badge": None if offer is None else offer.badge,
        "stale": bool(obs.stale),
        "source": obs.source,
    }
