from datetime import datetime, timezone

from flask_login import UserMixin

from backend.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_pro = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)

    def has_pro(self):
        return bool(self.is_admin or self.is_pro)

    def to_public(self):
        return {
            "id": self.id,
            "email": self.email,
            "is_admin": self.is_admin,
            "is_pro": self.has_pro(),
        }


class Invite(db.Model):
    __tablename__ = "invites"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(16), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    used_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    used_at = db.Column(db.DateTime, nullable=True)

    used_by = db.relationship("User", foreign_keys=[used_by_id])


class Plan(db.Model):
    __tablename__ = "plans"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    prefs_json = db.Column(db.Text, nullable=False)
    plan_json = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)


class CupboardItem(db.Model):
    __tablename__ = "cupboard_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=0)
    unit = db.Column(db.String(16), nullable=False, default="g")
    source = db.Column(db.String(32), nullable=False, default="manual")


def ensure_schema():
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if "users" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("users")}
        if "is_pro" not in cols:
            db.session.execute(text("ALTER TABLE users ADD COLUMN is_pro BOOLEAN DEFAULT 0 NOT NULL"))
            db.session.commit()
