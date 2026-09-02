from datetime import datetime, timezone

from backend.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


class Ingredient(db.Model):
    __tablename__ = "ingredients"

    id = db.Column(db.String(64), primary_key=True)
    canonical_name = db.Column(db.String(120), nullable=False)
    default_unit = db.Column(db.String(16), nullable=False, default="g")
    aliases = db.Column(db.JSON, nullable=False, default=list)


class Sku(db.Model):
    __tablename__ = "skus"

    id = db.Column(db.Integer, primary_key=True)
    store = db.Column(db.String(32), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    brand = db.Column(db.String(120), nullable=True)
    ean = db.Column(db.String(32), nullable=True, index=True)
    pack_size = db.Column(db.Float, nullable=False)
    pack_unit = db.Column(db.String(16), nullable=False)
    aisle = db.Column(db.String(64), nullable=False, default="Sonstiges")

    __table_args__ = (
        db.UniqueConstraint("store", "ean", name="uq_sku_store_ean"),
    )


class PriceObservation(db.Model):
    __tablename__ = "price_observations"

    id = db.Column(db.Integer, primary_key=True)
    sku_id = db.Column(db.Integer, db.ForeignKey("skus.id"), nullable=False, index=True)
    amount_eur = db.Column(db.Float, nullable=False)
    observed_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    source = db.Column(db.String(32), nullable=False, default="admin")
    confidence = db.Column(db.String(16), nullable=False, default="high")
    is_current = db.Column(db.Boolean, nullable=False, default=True, index=True)
    stale = db.Column(db.Boolean, nullable=False, default=False)

    sku = db.relationship("Sku", backref=db.backref("observations", lazy="dynamic"))


class Offer(db.Model):
    __tablename__ = "offers"

    id = db.Column(db.Integer, primary_key=True)
    sku_id = db.Column(db.Integer, db.ForeignKey("skus.id"), nullable=False, index=True)
    week = db.Column(db.String(16), nullable=False, index=True)
    offer_price = db.Column(db.Float, nullable=False)
    regular_price = db.Column(db.Float, nullable=True)
    badge = db.Column(db.String(64), nullable=True)
    valid_from = db.Column(db.DateTime, nullable=True)
    valid_to = db.Column(db.DateTime, nullable=True)
    source = db.Column(db.String(32), nullable=False, default="prospekt")
    is_current = db.Column(db.Boolean, nullable=False, default=True)

    sku = db.relationship("Sku", backref=db.backref("offers", lazy="dynamic"))


class Recipe(db.Model):
    __tablename__ = "recipes"

    id = db.Column(db.String(64), primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    cuisine = db.Column(db.String(64), nullable=False, default="international")
    locale = db.Column(db.String(8), nullable=False, default="de")
    slot = db.Column(db.String(32), nullable=False)
    active_time_minutes = db.Column(db.Integer, nullable=False)
    servings = db.Column(db.Integer, nullable=False, default=2)
    status = db.Column(db.String(16), nullable=False, default="draft", index=True)
    diets = db.Column(db.JSON, nullable=False, default=list)
    allergens = db.Column(db.JSON, nullable=False, default=list)
    calories = db.Column(db.Integer, nullable=False, default=0)
    protein = db.Column(db.Integer, nullable=False, default=0)
    carbs = db.Column(db.Integer, nullable=False, default=0)
    fat = db.Column(db.Integer, nullable=False, default=0)
    fiber = db.Column(db.Integer, nullable=False, default=0)
    steps = db.Column(db.JSON, nullable=False, default=list)
    equipment = db.Column(db.JSON, nullable=False, default=list)

    lines = db.relationship(
        "RecipeLine",
        backref="recipe",
        cascade="all, delete-orphan",
        order_by="RecipeLine.position",
    )


class RecipeLine(db.Model):
    __tablename__ = "recipe_lines"

    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.String(64), db.ForeignKey("recipes.id"), nullable=False, index=True)
    ingredient_id = db.Column(db.String(64), db.ForeignKey("ingredients.id"), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(16), nullable=False)
    notes = db.Column(db.String(200), nullable=True)
    position = db.Column(db.Integer, nullable=False, default=0)

    ingredient = db.relationship("Ingredient")


class IngredientSku(db.Model):
    __tablename__ = "ingredient_skus"

    id = db.Column(db.Integer, primary_key=True)
    ingredient_id = db.Column(db.String(64), db.ForeignKey("ingredients.id"), nullable=False)
    store = db.Column(db.String(32), nullable=False)
    sku_id = db.Column(db.Integer, db.ForeignKey("skus.id"), nullable=False)
    is_substitute = db.Column(db.Boolean, nullable=False, default=False)
    yield_factor = db.Column(db.Float, nullable=False, default=1.0)

    ingredient = db.relationship("Ingredient")
    sku = db.relationship("Sku")

    __table_args__ = (
        db.UniqueConstraint("ingredient_id", "store", "sku_id", name="uq_ingredient_store_sku"),
    )


class IngestBatch(db.Model):
    __tablename__ = "ingest_batches"

    id = db.Column(db.Integer, primary_key=True)
    store = db.Column(db.String(32), nullable=False, index=True)
    week = db.Column(db.String(16), nullable=False)
    source = db.Column(db.String(64), nullable=False, default="fixture")
    status = db.Column(db.String(16), nullable=False, default="pending", index=True)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)

    items = db.relationship(
        "IngestItem",
        backref="batch",
        cascade="all, delete-orphan",
        order_by="IngestItem.id",
    )


class IngestItem(db.Model):
    __tablename__ = "ingest_items"

    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("ingest_batches.id"), nullable=False, index=True)
    action = db.Column(db.String(32), nullable=False, default="upsert")
    name = db.Column(db.String(200), nullable=False)
    brand = db.Column(db.String(120), nullable=True)
    ean = db.Column(db.String(32), nullable=True)
    pack_size = db.Column(db.Float, nullable=False)
    pack_unit = db.Column(db.String(16), nullable=False)
    aisle = db.Column(db.String(64), nullable=False, default="Sonstiges")
    amount_eur = db.Column(db.Float, nullable=True)
    offer_price = db.Column(db.Float, nullable=True)
    regular_price = db.Column(db.Float, nullable=True)
    badge = db.Column(db.String(64), nullable=True)
    status = db.Column(db.String(16), nullable=False, default="pending")
    sku_id = db.Column(db.Integer, db.ForeignKey("skus.id"), nullable=True)


class FrozenPack(db.Model):
    __tablename__ = "frozen_packs"

    id = db.Column(db.Integer, primary_key=True)
    week = db.Column(db.String(16), nullable=False, index=True)
    store = db.Column(db.String(32), nullable=False, index=True)
    revision = db.Column(db.Integer, nullable=False)
    match_json = db.Column(db.JSON, nullable=False)
    markdown = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("week", "store", "revision", name="uq_pack_week_store_rev"),
    )
