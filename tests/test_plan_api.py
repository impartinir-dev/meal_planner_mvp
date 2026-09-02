def _login_admin(client):
    client.post("/api/auth/login", json={"email": "admin@test.local", "password": "testdevpass"})


def test_seed_admin_can_be_looked_up(app):
    from backend.models import User

    with app.app_context():
        user = User.query.filter_by(email="admin@test.local").first()
        assert user is not None
        assert user.is_admin is True


def test_generate_and_fetch_plan(client):
    _login_admin(client)
    body = {
        "store": "Lidl",
        "diet": "High-Protein",
        "budget": 55,
        "days": 5,
        "calories": 2100,
        "protein": 130,
        "pantry": ["Olivenöl"],
        "portions": 1,
    }
    r = client.post("/api/plan", json=body)
    assert r.status_code == 200
    plan = r.get_json()["plan"]
    assert plan["days"] == 5
    assert "deal_week" in plan
    g = client.get("/api/plan")
    assert g.status_code == 200
    assert g.get_json()["plan"]["store"] == "Lidl"


def test_swap_persists(client):
    _login_admin(client)
    client.post("/api/plan", json={
        "store": "Lidl",
        "diet": "All",
        "budget": 70,
        "days": 5,
        "calories": 2000,
        "protein": 120,
        "pantry": [],
        "portions": 1,
    })
    plan = client.get("/api/plan").get_json()["plan"]
    meal = plan["days_plan"][0]["meals"][0]
    r = client.post("/api/plan/swap", json={
        "day_index": 0,
        "category": meal["category"],
        "current_id": meal["id"],
    })
    assert r.status_code == 200
    new_meal = r.get_json()["plan"]["days_plan"][0]["meals"][0]
    assert new_meal["id"] != meal["id"]
