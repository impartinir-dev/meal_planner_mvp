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
    plan_tier = db.Column(db.String(16), default="free", nullable=False)
    household_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)

    def tier(self):
        if self.is_admin:
            return "premium"
        t = (self.plan_tier or "free").lower()
        if t in ("premium", "plus"):
            return t
        if self.is_pro:
            return "plus"
        return "free"

    def has_plus(self):
        return self.tier() in ("plus", "premium") or bool(self.is_admin)

    def has_premium(self):
        return self.tier() == "premium" or bool(self.is_admin)

    def has_pro(self):
        return self.has_plus()

    def to_public(self):
        return {
            "id": self.id,
            "email": self.email,
            "is_admin": self.is_admin,
            "is_pro": self.has_plus(),
            "plan_tier": self.tier(),
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


class RecipeBan(db.Model):
    __tablename__ = "recipe_bans"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    recipe_id = db.Column(db.String(32), nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)

    __table_args__ = (db.UniqueConstraint("user_id", "recipe_id", name="uq_user_recipe_ban"),)


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
        cols = {c["name"] for c in inspector.get_columns("users")}
        if "plan_tier" not in cols:
            db.session.execute(text("ALTER TABLE users ADD COLUMN plan_tier VARCHAR(16) DEFAULT 'free' NOT NULL"))
            db.session.commit()
        cols = {c["name"] for c in inspector.get_columns("users")}
        if "household_json" not in cols:
            db.session.execute(text("ALTER TABLE users ADD COLUMN household_json TEXT"))
            db.session.commit()
    if "recipes" in inspector.get_table_names():
        rcols = {c["name"] for c in inspector.get_columns("recipes")}
        if "equipment" not in rcols:
            db.session.execute(text("ALTER TABLE recipes ADD COLUMN equipment TEXT DEFAULT '[]' NOT NULL"))
            db.session.commit()
