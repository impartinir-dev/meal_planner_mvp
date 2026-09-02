from backend.seed import create_invite


def test_register_without_invite_fails(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "a@b.c", "password": "password1", "invite_code": "NOPE"},
    )
    assert r.status_code == 400


def test_register_login_me_logout(client, app):
    with app.app_context():
        code = create_invite().code
    r = client.post(
        "/api/auth/register",
        json={"email": "Ada@B.C", "password": "password1", "invite_code": code},
    )
    assert r.status_code == 201
    assert r.get_json()["user"]["email"] == "ada@b.c"
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401
    assert client.post(
        "/api/auth/login",
        json={"email": "ada@b.c", "password": "password1"},
    ).status_code == 200


def test_me_requires_login(client):
    assert client.get("/api/auth/me").status_code == 401


def test_plan_routes_require_login(client):
    assert client.get("/api/plan").status_code == 401
