import pytest

from backend import create_app
from backend.extensions import db
from backend.seed import seed_admin


@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test",
        "SESSION_COOKIE_SECURE": False,
    })
    with app.app_context():
        db.create_all()
        seed_admin("admin@test.local", "testdevpass")
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
