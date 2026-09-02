import os
import secrets
import string

from werkzeug.security import generate_password_hash

from backend.extensions import db
from backend.models import Invite, User

ALPHABET = string.ascii_uppercase + string.digits


def seed_admin(email, password):
    email = email.strip().lower()
    user = User.query.filter_by(email=email).first()
    if user:
        return user
    user = User(
        email=email,
        password_hash=generate_password_hash(password, method="scrypt"),
        is_admin=True,
        is_pro=True,
    )
    db.session.add(user)
    db.session.commit()
    return user


def create_invite():
    for _ in range(20):
        code = "".join(secrets.choice(ALPHABET) for _ in range(8))
        if Invite.query.filter_by(code=code).first() is None:
            invite = Invite(code=code)
            db.session.add(invite)
            db.session.commit()
            return invite
    raise RuntimeError("Could not allocate a unique invite code")


def main():
    from backend import create_app

    app = create_app()
    email = os.environ.get("ADMIN_EMAIL", "admin@localhost")
    password = os.environ.get("ADMIN_PASSWORD", "changeme-now")
    with app.app_context():
        admin = seed_admin(email, password)
        print(f"Admin: {admin.email}")
        unused = Invite.query.filter_by(used_by_id=None).all()
        while len(unused) < 3:
            unused.append(create_invite())
        print("Invite codes:")
        for inv in unused[:10]:
            print(f"  {inv.code}")


if __name__ == "__main__":
    main()
