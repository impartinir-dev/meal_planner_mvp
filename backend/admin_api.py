import json
import os

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from werkzeug.security import generate_password_hash

from backend.algorithm import PACK_SIZES, reload_data
from backend.extensions import db
from backend.models import User

admin_bp = Blueprint("admin", __name__)

DEALS_PATH = os.path.join(os.path.dirname(__file__), "data", "deals.json")


def _admin():
    if not current_user.is_authenticated or not current_user.is_admin:
        return jsonify({"error": "forbidden"}), 403
    return None


@admin_bp.get("/deals")
@login_required
def get_deals():
    denied = _admin()
    if denied:
        return denied
    with open(DEALS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    ingredients = sorted(PACK_SIZES.keys())
    return jsonify({"deals": data, "ingredients": ingredients})


@admin_bp.put("/deals")
@login_required
def put_deals():
    denied = _admin()
    if denied:
        return denied
    payload = request.get_json(silent=True) or {}
    week = str(payload.get("week") or "").strip()
    stores = payload.get("stores")
    if not week or not isinstance(stores, dict):
        return jsonify({"error": "invalid_deals"}), 400
    data = {"week": week, "stores": stores}
    with open(DEALS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    reload_data()
    return jsonify({"ok": True, "week": week})


@admin_bp.get("/users")
@login_required
def list_users():
    denied = _admin()
    if denied:
        return denied
    users = User.query.order_by(User.created_at.asc()).all()
    return jsonify({
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "is_admin": u.is_admin,
                "is_pro": u.has_pro(),
            }
            for u in users
        ]
    })


@admin_bp.post("/users/<int:user_id>/password")
@login_required
def reset_password(user_id):
    denied = _admin()
    if denied:
        return denied
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "not_found"}), 404
    password = str((request.get_json(silent=True) or {}).get("password") or "")
    if len(password) < 8:
        return jsonify({"error": "password_too_short"}), 400
    user.password_hash = generate_password_hash(password, method="scrypt")
    db.session.commit()
    return jsonify({"ok": True})


@admin_bp.post("/users/<int:user_id>/pro")
@login_required
def set_pro(user_id):
    denied = _admin()
    if denied:
        return denied
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "not_found"}), 404
    flag = bool((request.get_json(silent=True) or {}).get("is_pro"))
    user.is_pro = flag
    db.session.commit()
    return jsonify({"ok": True, "is_pro": user.has_pro()})
