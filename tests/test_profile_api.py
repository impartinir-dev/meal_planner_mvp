from backend.models import User


def _login(client):
    client.post("/api/auth/login", json={"email": "admin@test.local", "password": "testdevpass"})


def test_profile_defaults_to_self(client):
    _login(client)
    r = client.get("/api/profile")
    assert r.status_code == 200
    body = r.get_json()
    assert body["email"] == "admin@test.local"
    assert len(body["members"]) == 1
    assert body["members"][0]["name"] == "Ich"
    assert body["members"][0]["role"] == "ich"


def test_profile_put_round_trip(client, app):
    _login(client)
    payload = {
        "members": [
            {"id": "self", "name": "Alex", "role": "ich", "calories": 2100, "protein": 130},
            {"id": "m2", "name": "Sam", "role": "mitbewohner", "calories": 1900, "protein": 100},
            {"id": "m3", "name": "Kim", "role": "kind", "calories": 1600, "protein": 80},
        ]
    }
    r = client.put("/api/profile", json=payload)
    assert r.status_code == 200
    members = r.get_json()["members"]
    assert [m["name"] for m in members] == ["Alex", "Sam", "Kim"]
    assert [m["role"] for m in members] == ["ich", "mitbewohner", "kind"]
    again = client.get("/api/profile").get_json()["members"]
    assert [m["name"] for m in again] == ["Alex", "Sam", "Kim"]
    with app.app_context():
        user = User.query.filter_by(email="admin@test.local").one()
        assert user.household_json
        assert "mitbewohner" in user.household_json


def test_profile_empty_members_becomes_self(client):
    _login(client)
    r = client.put("/api/profile", json={"members": []})
    assert r.status_code == 200
    members = r.get_json()["members"]
    assert len(members) == 1
    assert members[0]["role"] == "ich"


def test_profile_caps_at_six(client):
    _login(client)
    people = [{"name": f"P{i}", "role": "andere", "calories": 2000, "protein": 100} for i in range(8)]
    r = client.put("/api/profile", json={"members": people})
    assert r.status_code == 200
    assert len(r.get_json()["members"]) == 6


def test_create_plan_writes_household(client):
    _login(client)
    r = client.post("/api/plan", json={
        "store": "Lidl",
        "diet": "All",
        "budget": 80,
        "days": 5,
        "members": [
            {"id": "a", "name": "Anna", "role": "ich", "calories": 1800, "protein": 110},
            {"id": "b", "name": "Ben", "role": "partner", "calories": 2400, "protein": 160},
        ],
        "pantry": [],
        "exclude": [],
    })
    assert r.status_code == 200
    profile = client.get("/api/profile").get_json()["members"]
    assert [m["name"] for m in profile] == ["Anna", "Ben"]
    assert profile[1]["role"] == "partner"
