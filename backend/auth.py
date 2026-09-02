import re

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from backend.extensions import db
from backend.models import Invite, User

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _json():
    return request.get_json(silent=True) or {}


@auth_bp.post("/register")
def register():
    data = _json()
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")
    invite_code = str(data.get("invite_code") or "").strip().upper()

    if not EMAIL_RE.match(email):
        return jsonify({"error": "invalid_email"}), 400
    if len(password) < 8:
        return jsonify({"error": "password_too_short"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "email_taken"}), 400

    invite = Invite.query.filter_by(code=invite_code).first()
    if invite is None or invite.used_by_id is not None:
        return jsonify({"error": "invalid_invite"}), 400

    user = User(
        email=email,
        password_hash=generate_password_hash(password, method="scrypt"),
        is_admin=False,
    )
    db.session.add(user)
    db.session.flush()
    from datetime import datetime, timezone

    invite.used_by_id = user.id
    invite.used_at = datetime.now(timezone.utc)
    db.session.commit()
    login_user(user)
    return jsonify({"user": user.to_public()}), 201


@auth_bp.post("/login")
def login():
    data = _json()
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")
    user = User.query.filter_by(email=email).first()
    if user is None or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "invalid_credentials"}), 401
    login_user(user)
    return jsonify({"user": user.to_public()}), 200


@auth_bp.post("/logout")
def logout():
    logout_user()
    return ("", 204)


@auth_bp.get("/me")
def me():
    if not current_user.is_authenticated:
        return jsonify({"error": "unauthorized"}), 401
    return jsonify(current_user.to_public()), 200
