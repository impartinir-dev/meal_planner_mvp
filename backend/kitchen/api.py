from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from backend.extensions import db
from backend.kitchen.catalog import (
    CatalogError,
    create_ingredient,
    create_recipe,
    create_sku,
    map_ingredient_sku,
    record_offer,
    record_price,
)
from backend.kitchen.matcher import MatchError, match_week, swap_slot
from backend.kitchen.models import FrozenPack, Ingredient, Recipe, Sku
from backend.kitchen.pack import freeze_pack
from backend.kitchen.serialize import live_stores, recipe_public, sku_public
from backend.kitchen.shoppable import shoppable_recipe_ids


kitchen_bp = Blueprint("kitchen", __name__)


def _admin_denied():
    if not current_user.is_authenticated or not current_user.is_admin:
        return jsonify({"error": "forbidden"}), 403
    return None


def _json():
    return request.get_json(silent=True) or {}


@kitchen_bp.get("/stores")
@login_required
def list_stores():
    return jsonify({"stores": live_stores()})


@kitchen_bp.get("/recipes")
@login_required
def list_recipes():
    store = request.args.get("store")
    ten_minute = request.args.get("ten_minute") in ("1", "true", "yes")
    q = Recipe.query.filter_by(status="published")
    recipes = q.all()
    if store:
        allowed = set(shoppable_recipe_ids(store, ten_minute_only=ten_minute))
        recipes = [r for r in recipes if r.id in allowed]
    elif ten_minute:
        recipes = [r for r in recipes if r.active_time_minutes <= 10]
    return jsonify({"recipes": [recipe_public(r, store=store) for r in recipes]})


@kitchen_bp.get("/recipes/<recipe_id>")
@login_required
def get_recipe(recipe_id):
    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None or recipe.status != "published":
        if recipe is None or not current_user.is_admin:
            return jsonify({"error": "not_found"}), 404
    store = request.args.get("store")
    return jsonify(recipe_public(recipe, store=store))


@kitchen_bp.post("/admin/ingredients")
@login_required
def admin_create_ingredient():
    denied = _admin_denied()
    if denied:
        return denied
    data = _json()
    try:
        row = create_ingredient(
            data.get("id"),
            data.get("canonical_name"),
            default_unit=data.get("default_unit") or "g",
            aliases=data.get("aliases") or [],
        )
        db.session.commit()
    except CatalogError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    return jsonify({"id": row.id, "canonical_name": row.canonical_name}), 201


@kitchen_bp.post("/admin/skus")
@login_required
def admin_create_sku():
    denied = _admin_denied()
    if denied:
        return denied
    data = _json()
    try:
        row = create_sku(
            data.get("store"),
            data.get("name"),
            data.get("pack_size"),
            data.get("pack_unit"),
            aisle=data.get("aisle") or "Sonstiges",
            brand=data.get("brand"),
            ean=data.get("ean"),
        )
        db.session.commit()
    except CatalogError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    return jsonify(sku_public(row)), 201


@kitchen_bp.post("/admin/prices")
@login_required
def admin_record_price():
    denied = _admin_denied()
    if denied:
        return denied
    data = _json()
    try:
        record_price(data.get("sku_id"), data.get("amount_eur"), source=data.get("source") or "admin")
        if data.get("offer_price") and data.get("week"):
            record_offer(
                data["sku_id"],
                data["week"],
                data["offer_price"],
                regular_price=data.get("regular_price"),
                badge=data.get("badge"),
            )
        db.session.commit()
    except CatalogError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    sku = db.session.get(Sku, data.get("sku_id"))
    return jsonify(sku_public(sku))


@kitchen_bp.post("/admin/maps")
@login_required
def admin_map():
    denied = _admin_denied()
    if denied:
        return denied
    data = _json()
    try:
        row = map_ingredient_sku(
            data.get("ingredient_id"),
            data.get("store"),
            data.get("sku_id"),
            is_substitute=bool(data.get("is_substitute")),
            yield_factor=data.get("yield_factor") or 1.0,
        )
        db.session.commit()
    except CatalogError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    return jsonify({
        "ingredient_id": row.ingredient_id,
        "store": row.store,
        "sku_id": row.sku_id,
        "is_substitute": row.is_substitute,
    }), 201


@kitchen_bp.post("/admin/recipes")
@login_required
def admin_create_recipe():
    denied = _admin_denied()
    if denied:
        return denied
    data = _json()
    try:
        row = create_recipe(
            data.get("id"),
            data.get("title"),
            slot=data.get("slot"),
            active_time_minutes=data.get("active_time_minutes"),
            lines=data.get("lines") or [],
            steps=data.get("steps") or [],
            cuisine=data.get("cuisine") or "international",
            locale=data.get("locale") or "de",
            servings=data.get("servings") or 2,
            status=data.get("status") or "draft",
            diets=data.get("diets"),
            allergens=data.get("allergens"),
            macros=data.get("macros"),
        )
        db.session.commit()
    except CatalogError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    return jsonify(recipe_public(row)), 201


@kitchen_bp.get("/admin/ingredients")
@login_required
def admin_list_ingredients():
    denied = _admin_denied()
    if denied:
        return denied
    rows = Ingredient.query.order_by(Ingredient.id).all()
    return jsonify({
        "ingredients": [
            {
                "id": r.id,
                "canonical_name": r.canonical_name,
                "default_unit": r.default_unit,
                "aliases": r.aliases or [],
            }
            for r in rows
        ]
    })


def _locked_map(items):
    out = {}
    for item in items or []:
        out[(int(item["day"]), item["slot"])] = item["recipe_id"]
    return out


def _forbidden_map(items):
    out = {}
    for item in items or []:
        out.setdefault((int(item["day"]), item["slot"]), set()).add(item["recipe_id"])
    return out


def _match_args(data):
    return dict(
        store=data.get("store"),
        week=data.get("week") or "2026-W36",
        days=data.get("days") or 7,
        budget=data.get("budget") or 80,
        target_calories=data.get("target_calories") or 2000,
        target_protein=data.get("target_protein") or 120,
        diet=data.get("diet"),
        pantry=data.get("pantry") or [],
        ten_minute_only=bool(data.get("ten_minute")),
        locked=_locked_map(data.get("locked")),
        forbidden=_forbidden_map(data.get("forbidden")),
        banned_ids=data.get("banned_ids") or [],
    )


def _pack_public(row):
    return {
        "id": row.id,
        "week": row.week,
        "store": row.store,
        "revision": row.revision,
        "markdown": row.markdown,
        "match": row.match_json,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@kitchen_bp.post("/match")
@login_required
def create_match():
    data = _json()
    try:
        result = match_week(**_match_args(data))
    except MatchError as exc:
        code = 400 if exc.code == "unknown_store" else 409
        return jsonify({"error": exc.code, "message": str(exc)}), code
    return jsonify(result)


@kitchen_bp.post("/match/swap")
@login_required
def swap_match():
    data = _json()
    match = data.get("match")
    if not match:
        return jsonify({"error": "match_required"}), 400
    try:
        result = swap_slot(match, int(data["day"]), data["slot"])
    except MatchError as exc:
        return jsonify({"error": exc.code, "message": str(exc)}), 409
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "invalid_swap"}), 400
    return jsonify(result)


@kitchen_bp.post("/packs")
@login_required
def create_pack():
    data = _json()
    match = data.get("match")
    if not match:
        try:
            match = match_week(**_match_args(data))
        except MatchError as exc:
            code = 400 if exc.code == "unknown_store" else 409
            return jsonify({"error": exc.code, "message": str(exc)}), code
    row = freeze_pack(match)
    db.session.commit()
    return jsonify(_pack_public(row)), 201


@kitchen_bp.get("/packs/<int:pack_id>")
@login_required
def get_pack(pack_id):
    row = db.session.get(FrozenPack, pack_id)
    if row is None:
        return jsonify({"error": "not_found"}), 404
    return jsonify(_pack_public(row))
