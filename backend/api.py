import json

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from backend.allergens import ALLERGEN_OPTIONS
from backend.extensions import db
from backend.kitchen.bridge import (
    generate_client_plan,
    kitchen_ingredients,
    normalize_store,
    pantry_staples,
    swap_client_plan,
)
from backend.kitchen.constants import DEFAULT_EQUIPMENT, EQUIPMENT_IDS
from backend.kitchen.matcher import MatchError
from backend.kitchen.serialize import live_stores as kitchen_live_stores
from backend.models import CupboardItem, Invite, Plan, RecipeBan, User
from backend.nutrition import calculate_needs
from backend.seed import create_invite
from backend.version import APP_VERSION, PREMIUM_PRICE_EUR, PRO_PERIOD, PRO_PRICE_EUR

api_bp = Blueprint("api", __name__)

DIETS = [
    {"id": "All", "name": "Flexitarisch", "icon": "utensils", "desc": "Ausgewogen & vielseitig"},
    {"id": "High-Protein", "name": "High-Protein", "icon": "dumbbell", "desc": "Maximaler Muskelaufbau"},
    {"id": "Vegetarisch", "name": "Vegetarisch", "icon": "salad", "desc": "Ohne Fleisch & Fisch"},
    {"id": "Vegan", "name": "100% Vegan", "icon": "sprout", "desc": "Rein pflanzlich"},
    {"id": "Low-Carb", "name": "Low-Carb", "icon": "flame", "desc": "Wenig Kohlenhydrate"},
    {"id": "Clean", "name": "Clean Eating", "icon": "sparkles", "desc": "Frisch & unverarbeitet"},
    {"id": "Sparfuchs", "name": "Sparfuchs", "icon": "coins", "desc": "Günstigste Sättigung"},
]

DIET_IDS = {d["id"] for d in DIETS}

MEMBER_ROLES = ("ich", "partner", "kind", "mitbewohner", "andere")
DEFAULT_MEMBER = {"id": "self", "name": "Ich", "role": "ich", "calories": 2200, "protein": 140}


def parse_members(raw, calories=2200, protein=140):
    members = []
    if isinstance(raw, list):
        for item in raw[:6]:
            if not isinstance(item, dict):
                continue
            try:
                mc = int(item.get("calories", calories))
                mp = int(item.get("protein", protein))
            except (TypeError, ValueError):
                return None, ("invalid_member", 400)
            role = str(item.get("role") or "").strip().lower()
            if role not in MEMBER_ROLES:
                role = "ich" if not members else "andere"
            name = str(item.get("name") or "").strip()[:40]
            if not name:
                name = "Ich" if role == "ich" else f"Person {len(members) + 1}"
            members.append({
                "id": str(item.get("id") or f"m{len(members)+1}"),
                "name": name,
                "role": role,
                "calories": max(1200, min(4000, mc)),
                "protein": max(50, min(250, mp)),
            })
    if not members:
        row = dict(DEFAULT_MEMBER)
        row["calories"] = max(1200, min(4000, int(calories)))
        row["protein"] = max(50, min(250, int(protein)))
        members = [row]
    return members, None


def write_household(user, members):
    user.household_json = json.dumps(members, ensure_ascii=False)


def read_household(user):
    if user.household_json:
        try:
            raw = json.loads(user.household_json)
        except (TypeError, ValueError):
            raw = None
        members, _ = parse_members(raw)
        return members
    row = Plan.query.filter_by(user_id=user.id).first()
    if row:
        try:
            prefs = json.loads(row.prefs_json or "{}")
        except (TypeError, ValueError):
            prefs = {}
        members, _ = parse_members(prefs.get("members"))
        return members
    members, _ = parse_members(None)
    return members


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
        "premium_price": PREMIUM_PRICE_EUR,
        "pro_period": PRO_PERIOD,
    })


@api_bp.get("/meta")
@login_required
def meta():
    stores = kitchen_live_stores()
    deal_week = None
    if stores:
        from backend.kitchen.bridge import active_week
        deal_week = active_week(stores[0]["id"])
    return jsonify({
        "stores": stores,
        "diets": DIETS,
        "pantry_staples": pantry_staples(),
        "allergens": ALLERGEN_OPTIONS,
        "ingredients": kitchen_ingredients(),
        "deal_week": deal_week,
        "version": APP_VERSION,
        "pro_price": PRO_PRICE_EUR,
        "premium_price": PREMIUM_PRICE_EUR,
        "pro_period": PRO_PERIOD,
        "equipment": [{"id": e, "name": e} for e in EQUIPMENT_IDS],
        "calories_range": {"min": 1400, "max": 3600, "step": 50},
        "protein_range": {"min": 60, "max": 240, "step": 5},
        "budget_range": {"min": 15, "max": 150, "step": 5},
        "portions_range": {"min": 1, "max": 6},
        "days_options": [5, 7],
        "activity_levels": [
            {"id": "sedentary", "name": "Sitzend (Büro)"},
            {"id": "light", "name": "Leicht (1–2x Sport/Woche)"},
            {"id": "moderate", "name": "Moderat (3x Sport/Woche)"},
            {"id": "active", "name": "Aktiv (4–5x Sport/Woche)"},
            {"id": "very", "name": "Sehr aktiv (täglich / körperliche Arbeit)"},
        ],
        "goals": [
            {"id": "lose", "name": "Abnehmen"},
            {"id": "maintain", "name": "Gewicht halten"},
            {"id": "gain", "name": "Zunehmen / Aufbau"},
        ],
    })


@api_bp.get("/profile")
@login_required
def get_profile():
    return jsonify({
        "email": current_user.email,
        "plan_tier": current_user.tier(),
        "members": read_household(current_user),
    })


@api_bp.put("/profile")
@login_required
def put_profile():
    data = request.get_json(silent=True) or {}
    members, err = parse_members(data.get("members"))
    if err:
        return jsonify({"error": err[0]}), err[1]
    write_household(current_user, members)
    db.session.commit()
    return jsonify({
        "email": current_user.email,
        "plan_tier": current_user.tier(),
        "members": members,
    })


@api_bp.get("/plan")
@login_required
def get_plan():
    row = Plan.query.filter_by(user_id=current_user.id).first()
    if row is None:
        return jsonify({"error": "no_plan"}), 404
    return jsonify(_dump_plan_row(row))


def _validate_prefs(data):
    store = normalize_store(data.get("store") or "lidl") or (data.get("store") or "lidl")
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
    live_ids = {s["id"] for s in kitchen_live_stores()}
    if store not in live_ids:
        return None, ("invalid_store", 400)
    if diet not in DIET_IDS:
        return None, ("invalid_diet", 400)
    if days not in (5, 7):
        return None, ("invalid_days", 400)
    if budget < 15 or budget > 250:
        return None, ("invalid_budget", 400)
    members, member_err = parse_members(data.get("members"), calories=calories, protein=protein)
    if member_err:
        return None, member_err
    portions = len(members)
    calories = int(round(sum(m["calories"] for m in members) / len(members)))
    protein = int(round(sum(m["protein"] for m in members) / len(members)))
    if calories < 1200 or calories > 4000:
        return None, ("invalid_calories", 400)
    if protein < 50 or protein > 250:
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
        "members": members,
        "equipment": _parse_equipment(data.get("equipment")),
    }
    return prefs, None


def _parse_equipment(raw):
    if not isinstance(raw, list) or not raw:
        return list(DEFAULT_EQUIPMENT)
    allowed = set(EQUIPMENT_IDS)
    tools = [str(x) for x in raw if str(x) in allowed]
    return tools or list(DEFAULT_EQUIPMENT)


def _banned_ids(user_id):
    return [row.recipe_id for row in RecipeBan.query.filter_by(user_id=user_id).all()]


@api_bp.post("/plan")
@login_required
def create_plan():
    data = request.get_json(silent=True) or {}
    prefs, err = _validate_prefs(data)
    if err:
        return jsonify({"error": err[0]}), err[1]
    try:
        plan = generate_client_plan(
            prefs,
            current_user.id,
            banned_ids=_banned_ids(current_user.id),
        )
    except MatchError as exc:
        code = 400 if exc.code == "unknown_store" else 409
        return jsonify({"error": exc.code, "message": str(exc)}), code
    row = Plan.query.filter_by(user_id=current_user.id).first()
    if row is None:
        row = Plan(user_id=current_user.id, prefs_json="{}", plan_json="{}")
        db.session.add(row)
    row.prefs_json = json.dumps(prefs, ensure_ascii=False)
    row.plan_json = json.dumps(plan, ensure_ascii=False)
    write_household(current_user, prefs["members"])
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
    plan = json.loads(row.plan_json)
    prefs = json.loads(row.prefs_json)
    try:
        swapped = swap_client_plan(plan, prefs, day_index, category)
    except MatchError:
        return jsonify({"error": "no_alternative"}), 404
    row.plan_json = json.dumps(swapped, ensure_ascii=False)
    db.session.commit()
    return jsonify(_dump_plan_row(row))


@api_bp.post("/calculator")
@login_required
def calculator():
    data = request.get_json(silent=True) or {}
    try:
        result = calculate_needs(
            sex=data.get("sex", "female"),
            age=data.get("age", 30),
            height_cm=data.get("height_cm", 170),
            weight_kg=data.get("weight_kg", 70),
            activity=data.get("activity", "moderate"),
            goal=data.get("goal", "maintain"),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@api_bp.get("/recipes/never-again")
@login_required
def list_never_again():
    return jsonify({"ids": _banned_ids(current_user.id)})


@api_bp.post("/recipes/<recipe_id>/never-again")
@login_required
def add_never_again(recipe_id):
    recipe_id = str(recipe_id)
    existing = RecipeBan.query.filter_by(user_id=current_user.id, recipe_id=recipe_id).first()
    if existing is None:
        db.session.add(RecipeBan(user_id=current_user.id, recipe_id=recipe_id))
        db.session.commit()
    row = Plan.query.filter_by(user_id=current_user.id).first()
    if row is None:
        return jsonify({"ids": _banned_ids(current_user.id), "plan": None})
    prefs = json.loads(row.prefs_json)
    plan = json.loads(row.plan_json)
    banned = _banned_ids(current_user.id)
    locked = {}
    for day in plan.get("days_plan") or []:
        for meal in day.get("meals") or []:
            if meal.get("locked"):
                locked[(day["day_index"], meal["category"])] = meal["id"]
    try:
        plan = generate_client_plan(
            prefs,
            current_user.id,
            banned_ids=banned,
            locked=locked,
        )
        plan["banned_ids"] = banned
        row.plan_json = json.dumps(plan, ensure_ascii=False)
    except MatchError:
        plan["banned_ids"] = banned
        row.plan_json = json.dumps(plan, ensure_ascii=False)
    db.session.commit()
    return jsonify({"ids": _banned_ids(current_user.id), **_dump_plan_row(row)})


@api_bp.delete("/recipes/<recipe_id>/never-again")
@login_required
def remove_never_again(recipe_id):
    RecipeBan.query.filter_by(user_id=current_user.id, recipe_id=str(recipe_id)).delete()
    db.session.commit()
    return jsonify({"ids": _banned_ids(current_user.id)})


@api_bp.post("/plan/log")
@login_required
def log_meal():
    row = Plan.query.filter_by(user_id=current_user.id).first()
    if row is None:
        return jsonify({"error": "no_plan"}), 404
    data = request.get_json(silent=True) or {}
    try:
        day_index = int(data.get("day_index", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_day"}), 400
    category = data.get("category", "Mittagessen")
    status = data.get("status")
    if status not in (None, "", "cooked", "skipped"):
        return jsonify({"error": "invalid_status"}), 400
    if status == "":
        status = None
    plan = json.loads(row.plan_json)
    days = plan.get("days_plan") or []
    if day_index < 0 or day_index >= len(days):
        return jsonify({"error": "invalid_day"}), 400
    found = False
    for meal in days[day_index].get("meals", []):
        if meal.get("category") == category:
            prev = meal.get("status")
            meal["status"] = status
            found = True
            if status == "cooked" and prev != "cooked" and current_user.has_plus():
                _deduct_meal(current_user.id, meal)
    if not found:
        return jsonify({"error": "not_found"}), 404
    row.plan_json = json.dumps(plan, ensure_ascii=False)
    db.session.commit()
    return jsonify(_dump_plan_row(row))


def _deduct_meal(user_id, meal):
    for ing in meal.get("ingredients") or []:
        name = str(ing.get("name") or "").strip()
        if not name:
            continue
        try:
            qty = float(ing.get("quantity") or 0)
        except (TypeError, ValueError):
            continue
        item = CupboardItem.query.filter_by(user_id=user_id, name=name).first()
        if item is None:
            continue
        item.quantity = max(0.0, float(item.quantity or 0) - qty)


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
