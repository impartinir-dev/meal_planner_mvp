from io import BytesIO

from backend.seed import create_invite
from backend.version import APP_VERSION


def _login_admin(client):
    client.post("/api/auth/login", json={"email": "admin@test.local", "password": "testdevpass"})


def test_version_is_public(client):
    r = client.get("/api/version")
    assert r.status_code == 200
    assert r.get_json()["version"] == APP_VERSION


def test_admin_can_reset_password_and_grant_pro(client, app):
    _login_admin(client)
    with app.app_context():
        code = create_invite().code
    client.post("/api/auth/logout")
    client.post(
        "/api/auth/register",
        json={"email": "free@test.local", "password": "password1", "invite_code": code},
    )
    client.post("/api/auth/logout")
    _login_admin(client)
    users = client.get("/api/admin/users").get_json()["users"]
    free = next(u for u in users if u["email"] == "free@test.local")
    assert free["is_pro"] is False
    assert client.post(
        f"/api/admin/users/{free['id']}/password",
        json={"password": "newpass12"},
    ).status_code == 200
    assert client.post(
        f"/api/admin/users/{free['id']}/pro",
        json={"is_pro": True},
    ).status_code == 200
    client.post("/api/auth/logout")
    assert client.post(
        "/api/auth/login",
        json={"email": "free@test.local", "password": "newpass12"},
    ).status_code == 200
    me = client.get("/api/auth/me").get_json()
    assert me["is_pro"] is True


def test_cupboard_requires_pro(client, app):
    _login_admin(client)
    with app.app_context():
        code = create_invite().code
    client.post("/api/auth/logout")
    client.post(
        "/api/auth/register",
        json={"email": "basic@test.local", "password": "password1", "invite_code": code},
    )
    r = client.get("/api/cupboard/")
    assert r.status_code == 402
    scan = client.post("/api/cupboard/scan", data={"file": (BytesIO(b"not-an-image"), "bon.jpg")})
    assert scan.status_code == 402


def test_admin_cupboard_and_lock(client):
    _login_admin(client)
    add = client.post("/api/cupboard/", json={"name": "Reis", "quantity": 500})
    assert add.status_code in (200, 201)
    listed = client.get("/api/cupboard/").get_json()["items"]
    assert any(i["name"] == "Reis" for i in listed)
    client.post("/api/plan", json={
        "store": "Lidl",
        "diet": "All",
        "budget": 80,
        "days": 5,
        "calories": 2000,
        "protein": 120,
        "pantry": [],
        "portions": 1,
        "exclude": ["Fisch"],
    })
    plan = client.get("/api/plan").get_json()["plan"]
    meal = plan["days_plan"][0]["meals"][0]
    locked = client.post("/api/plan/lock", json={
        "day_index": 0,
        "category": meal["category"],
        "locked": True,
    })
    assert locked.status_code == 200
    swapped = client.post("/api/plan/swap", json={
        "day_index": 0,
        "category": meal["category"],
        "current_id": meal["id"],
    })
    assert swapped.status_code == 404
    deals = client.get("/api/admin/deals")
    assert deals.status_code == 200
    assert "week" in deals.get_json()["deals"]
