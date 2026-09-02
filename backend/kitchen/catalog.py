from datetime import datetime, timezone

from backend.extensions import db
from backend.kitchen.constants import RECIPE_STATUSES, SLOTS, STORES, UNITS
from backend.kitchen.models import (
    Ingredient,
    IngredientSku,
    Offer,
    PriceObservation,
    Recipe,
    RecipeLine,
    Sku,
)


class CatalogError(ValueError):
    pass


def _utcnow():
    return datetime.now(timezone.utc)


def create_ingredient(ingredient_id, canonical_name, default_unit="g", aliases=None):
    ingredient_id = (ingredient_id or "").strip()
    canonical_name = (canonical_name or "").strip()
    if not ingredient_id or not canonical_name:
        raise CatalogError("ingredient id and name are required")
    if default_unit not in UNITS:
        raise CatalogError(f"unknown unit: {default_unit}")
    row = Ingredient(
        id=ingredient_id,
        canonical_name=canonical_name,
        default_unit=default_unit,
        aliases=list(aliases or []),
    )
    db.session.add(row)
    db.session.flush()
    return row


def create_sku(store, name, pack_size, pack_unit, aisle="Sonstiges", brand=None, ean=None):
    if store not in STORES:
        raise CatalogError(f"unknown store: {store}")
    if pack_unit not in UNITS:
        raise CatalogError(f"unknown unit: {pack_unit}")
    row = Sku(
        store=store,
        name=name,
        brand=brand,
        ean=ean,
        pack_size=pack_size,
        pack_unit=pack_unit,
        aisle=aisle,
    )
    db.session.add(row)
    db.session.flush()
    return row


def current_price(sku_id):
    return PriceObservation.query.filter_by(sku_id=sku_id, is_current=True).one_or_none()


def record_price(sku_id, amount_eur, source="admin", confidence="high", observed_at=None):
    """Set a new current pack price. Refuses empty amounts; never invents; never clobbers with None."""
    if amount_eur is None:
        raise CatalogError("price amount is required")
    try:
        amount = float(amount_eur)
    except (TypeError, ValueError) as exc:
        raise CatalogError("price amount is required") from exc
    if amount <= 0:
        raise CatalogError("price amount must be positive")
    if db.session.get(Sku, sku_id) is None:
        raise CatalogError(f"unknown sku: {sku_id}")

    PriceObservation.query.filter_by(sku_id=sku_id, is_current=True).update(
        {"is_current": False},
        synchronize_session=False,
    )
    row = PriceObservation(
        sku_id=sku_id,
        amount_eur=round(amount, 2),
        observed_at=observed_at or _utcnow(),
        source=source,
        confidence=confidence,
        is_current=True,
        stale=False,
    )
    db.session.add(row)
    db.session.flush()
    return row


def mark_prices_stale(sku_id):
    PriceObservation.query.filter_by(sku_id=sku_id, is_current=True).update(
        {"stale": True},
        synchronize_session=False,
    )


def record_offer(sku_id, week, offer_price, regular_price=None, badge=None, source="prospekt"):
    if offer_price is None or float(offer_price) <= 0:
        raise CatalogError("offer price is required")
    Offer.query.filter_by(sku_id=sku_id, is_current=True).update(
        {"is_current": False},
        synchronize_session=False,
    )
    row = Offer(
        sku_id=sku_id,
        week=week,
        offer_price=round(float(offer_price), 2),
        regular_price=None if regular_price is None else round(float(regular_price), 2),
        badge=badge,
        source=source,
        is_current=True,
    )
    db.session.add(row)
    db.session.flush()
    return row


def create_recipe(
    recipe_id,
    title,
    slot,
    active_time_minutes,
    lines,
    steps,
    cuisine="international",
    locale="de",
    servings=2,
    status="draft",
    diets=None,
    allergens=None,
    macros=None,
    equipment=None,
):
    recipe_id = (recipe_id or "").strip()
    title = (title or "").strip()
    if not recipe_id or not title:
        raise CatalogError("recipe id and title are required")
    if slot not in SLOTS:
        raise CatalogError(f"unknown slot: {slot}")
    if status not in RECIPE_STATUSES:
        raise CatalogError(f"unknown status: {status}")
    if not steps:
        raise CatalogError("recipe must have steps")
    if not lines:
        raise CatalogError("recipe must have ingredient lines")

    macros = macros or {}
    row = Recipe(
        id=recipe_id,
        title=title,
        cuisine=cuisine,
        locale=locale,
        slot=slot,
        active_time_minutes=int(active_time_minutes),
        servings=int(servings),
        status=status,
        diets=list(diets or []),
        allergens=list(allergens or []),
        calories=int(macros.get("calories") or 0),
        protein=int(macros.get("protein") or 0),
        carbs=int(macros.get("carbs") or 0),
        fat=int(macros.get("fat") or 0),
        fiber=int(macros.get("fiber") or 0),
        steps=list(steps),
        equipment=list(equipment or ["stovetop", "pan"]),
    )
    db.session.add(row)
    for i, line in enumerate(lines):
        ingredient_id = line["ingredient_id"]
        if db.session.get(Ingredient, ingredient_id) is None:
            raise CatalogError(f"unknown ingredient: {ingredient_id}")
        db.session.add(
            RecipeLine(
                recipe_id=recipe_id,
                ingredient_id=ingredient_id,
                quantity=float(line["quantity"]),
                unit=line.get("unit") or "g",
                notes=line.get("notes"),
                position=i,
            )
        )
    db.session.flush()
    return row


def map_ingredient_sku(ingredient_id, store, sku_id, is_substitute=False, yield_factor=1.0):
    if store not in STORES:
        raise CatalogError(f"unknown store: {store}")
    sku = db.session.get(Sku, sku_id)
    if sku is None:
        raise CatalogError(f"unknown sku: {sku_id}")
    if sku.store != store:
        raise CatalogError("sku store does not match map store")
    if db.session.get(Ingredient, ingredient_id) is None:
        raise CatalogError(f"unknown ingredient: {ingredient_id}")
    row = IngredientSku(
        ingredient_id=ingredient_id,
        store=store,
        sku_id=sku_id,
        is_substitute=bool(is_substitute),
        yield_factor=float(yield_factor),
    )
    db.session.add(row)
    db.session.flush()
    return row
