import json
import os

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from backend.allergens import ALLERGEN_OPTIONS
from backend.algorithm import PACK_SIZES, deal_week, generate_meal_plan, swap_single_meal
from backend.extensions import db
from backend.models import CupboardItem, Invite, Plan, User
from backend.seed import create_invite
from backend.version import APP_VERSION, PRO_PERIOD, PRO_PRICE_EUR

api_bp = Blueprint("api", __name__)

STORES = [
    {"id": "REWE", "name": "REWE", "badge": "Supermarkt", "logo_char": "R"},
    {"id": "Lidl", "name": "Lidl", "badge": "Discounter", "logo_char": "L"},
    {"id": "ALDI Süd", "name": "ALDI Süd", "badge": "Discounter", "logo_char": "A"},
    {"id": "Kaufland", "name": "Kaufland", "badge": "SB-Warenhaus", "logo_char": "K"},
    {"id": "EDEKA", "name": "EDEKA", "badge": "Supermarkt", "logo_char": "E"},
]

DIETS = [
    {"id": "All", "name": "Flexitarisch", "icon": "utensils", "desc": "Ausgewogen & vielseitig"},
    {"id": "High-Protein", "name": "High-Protein", "icon": "dumbbell", "desc": "Maximaler Muskelaufbau"},
    {"id": "Vegetarisch", "name": "Vegetarisch", "icon": "salad", "desc": "Ohne Fleisch & Fisch"},
    {"id": "Vegan", "name": "100% Vegan", "icon": "sprout", "desc": "Rein pflanzlich"},
    {"id": "Low-Carb", "name": "Low-Carb", "icon": "flame", "desc": "Wenig Kohlenhydrate"},
    {"id": "Clean", "name": "Clean Eating", "icon": "sparkles", "desc": "Frisch & unverarbeitet"},
    {"id": "Sparfuchs", "name": "Sparfuchs", "icon": "coins", "desc": "Günstigste Sättigung"},
]

STORE_IDS = {s["id"] for s in STORES}
DIET_IDS = {d["id"] for d in DIETS}


def _pantry_staples():
    path = os.path.join(os.path.dirname(__file__), "data", "pantry_staples.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _dump_plan_row(row):
    return {
        "prefs": json.loads(row.prefs_json),
        "plan": json.loads(row.plan_json),
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@api_bp.get("/version")
def version():
    return jsonify({
        "version": APP_VERSION,
        "pro_price": PRO_PRICE_EUR,
        "pro_period": PRO_PERIOD,
    })


@api_bp.get("/meta")
@login_required
def meta():
    return jsonify({
        "stores": STORES,
        "diets": DIETS,
        "pantry_staples": _pantry_staples(),
        "allergens": ALLERGEN_OPTIONS,
        "ingredients": sorted(PACK_SIZES.keys()),
        "deal_week": deal_week(),
        "version": APP_VERSION,
        "pro_price": PRO_PRICE_EUR,
        "pro_period": PRO_PERIOD,
        "calories_range": {"min": 1400, "max": 3600, "step": 50},
        "protein_range": {"min": 60, "max": 240, "step": 5},
        "budget_range": {"min": 15, "max": 150, "step": 5},
        "portions_range": {"min": 1, "max": 4},
        "days_options": [5, 7],
    })


@api_bp.get("/plan")
@login_required
def get_plan():
    row = Plan.query.filter_by(user_id=current_user.id).first()
    if row is None:
        return jsonify({"error": "no_plan"}), 404
    return jsonify(_dump_plan_row(row))


def _validate_prefs(data):
    store = data.get("store", "Lidl")
    diet = data.get("diet", "All")
    try:
        budget = float(data.get("budget", 50))
        days = int(data.get("days", 7))
        calories = int(data.get("calories", 2200))
        protein = int(data.get("protein", 140))
        portions = int(data.get("portions", 1))
    except (TypeError, ValueError):
        return None, ("invalid_numbers", 400)
    pantry = data.get("pantry") or []
    if not isinstance(pantry, list):
        return None, ("invalid_pantry", 400)
    pantry = [str(x) for x in pantry]
    exclude = data.get("exclude") or []
    if not isinstance(exclude, list):
        return None, ("invalid_exclude", 400)
    exclude = [str(x).strip() for x in exclude if str(x).strip()]
    if store not in STORE_IDS:
        return None, ("invalid_store", 400)
    if diet not in DIET_IDS:
        return None, ("invalid_diet", 400)
    if days not in (5, 7):
        return None, ("invalid_days", 400)
    if portions < 1 or portions > 4:
        return None, ("invalid_portions", 400)
    if budget < 15 or budget > 150:
        return None, ("invalid_budget", 400)
    if calories < 1400 or calories > 3600:
        return None, ("invalid_calories", 400)
    if protein < 60 or protein > 240:
        return None, ("invalid_protein", 400)
    prefs = {
        "store": store,
        "diet": diet,
        "budget": budget,
        "days": days,
        "calories": calories,
        "protein": protein,
        "pantry": pantry,
        "portions": portions,
        "exclude": exclude,
    }
    return prefs, None


def _cupboard_names(user_id):
    rows = CupboardItem.query.filter_by(user_id=user_id).all()
    return [r.name for r in rows if (r.quantity or 0) > 0]


@api_bp.post("/plan")
@login_required
def create_plan():
    data = request.get_json(silent=True) or {}
    prefs, err = _validate_prefs(data)
    if err:
        return jsonify({"error": err[0]}), err[1]
    pantry = list(prefs["pantry"])
    if current_user.has_pro():
        for name in _cupboard_names(current_user.id):
            if name not in pantry:
                pantry.append(name)
    plan = generate_meal_plan(
        store=prefs["store"],
        diet=prefs["diet"],
        budget=prefs["budget"],
        days=prefs["days"],
        target_calories=prefs["calories"],
        target_protein=prefs["protein"],
        pantry=pantry,
        portions=prefs["portions"],
        exclude=prefs.get("exclude") or [],
    )
    row = Plan.query.filter_by(user_id=current_user.id).first()
    if row is None:
        row = Plan(user_id=current_user.id, prefs_json="{}", plan_json="{}")
        db.session.add(row)
    row.prefs_json = json.dumps(prefs, ensure_ascii=False)
    row.plan_json = json.dumps(plan, ensure_ascii=False)
    db.session.commit()
    return jsonify(_dump_plan_row(row))


@api_bp.post("/plan/swap")
@login_required
def swap_plan_meal():
    row = Plan.query.filter_by(user_id=current_user.id).first()
    if row is None:
        return jsonify({"error": "no_plan"}), 404
    data = request.get_json(silent=True) or {}
    try:
        day_index = int(data.get("day_index", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_day"}), 400
    category = data.get("category", "Mittagessen")
    current_id = data.get("current_id", "")
    plan = json.loads(row.plan_json)
    swapped = swap_single_meal(plan, day_index, category, current_id)
    if swapped is None:
        return jsonify({"error": "no_alternative"}), 404
    row.plan_json = json.dumps(swapped, ensure_ascii=False)
    db.session.commit()
    return jsonify(_dump_plan_row(row))


@api_bp.post("/plan/lock")
@login_required
def lock_meal():
    row = Plan.query.filter_by(user_id=current_user.id).first()
    if row is None:
        return jsonify({"error": "no_plan"}), 404
    data = request.get_json(silent=True) or {}
    try:
        day_index = int(data.get("day_index", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_day"}), 400
    category = data.get("category", "Mittagessen")
    locked = bool(data.get("locked"))
    plan = json.loads(row.plan_json)
    days = plan.get("days_plan") or []
    if day_index < 0 or day_index >= len(days):
        return jsonify({"error": "invalid_day"}), 400
    found = False
    for meal in days[day_index].get("meals", []):
        if meal.get("category") == category:
            meal["locked"] = locked
            found = True
    if not found:
        return jsonify({"error": "not_found"}), 404
    row.plan_json = json.dumps(plan, ensure_ascii=False)
    db.session.commit()
    return jsonify(_dump_plan_row(row))


@api_bp.post("/invites")
@login_required
def post_invite():
    if not current_user.is_admin:
        return jsonify({"error": "forbidden"}), 403
    invite = create_invite()
    return jsonify({"code": invite.code}), 201


@api_bp.get("/invites")
@login_required
def list_invites():
    if not current_user.is_admin:
        return jsonify({"error": "forbidden"}), 403
    items = []
    for inv in Invite.query.order_by(Invite.created_at.desc()).all():
        email = None
        if inv.used_by_id:
            user = db.session.get(User, inv.used_by_id)
            email = user.email if user else None
        items.append({
            "code": inv.code,
            "used": inv.used_by_id is not None,
            "used_by_email": email,
        })
    return jsonify({"invites": items})
