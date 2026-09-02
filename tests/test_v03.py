from backend.algorithm import generate_meal_plan
from backend.nutrition import calculate_needs


def test_calculator_male_active_gain():
    r = calculate_needs("male", 30, 180, 80, activity="active", goal="gain")
    assert r["calories"] >= 2800
    assert 150 <= r["protein"] <= 180


def test_calculator_female_sedentary_lose():
    r = calculate_needs("female", 40, 165, 68, activity="sedentary", goal="lose")
    assert r["calories"] >= 1400
    assert r["calories"] < r["tdee"]
    assert r["protein"] >= 100


def test_never_again_id_is_not_planned():
    plan = generate_meal_plan("Lidl", "All", 80, 5, 2000, 120, banned_ids=["rec_53"])
    ids = [m["id"] for d in plan["days_plan"] for m in d["meals"]]
    assert "rec_53" not in ids


def test_complete_recipe_has_steps_and_salt():
    from backend.algorithm import RECIPES

    rec = next(r for r in RECIPES if r["id"] == "rec_65")
    assert isinstance(rec["instructions"], list) and len(rec["instructions"]) >= 3
    assert "Salz" in rec["ingredients"]
    assert "Pfeffer" in rec["ingredients"]


def test_members_create_plan(client):
    client.post("/api/auth/login", json={"email": "admin@test.local", "password": "testdevpass"})
    r = client.post("/api/plan", json={
        "store": "Lidl",
        "diet": "All",
        "budget": 90,
        "days": 5,
        "members": [
            {"id": "a", "name": "Anna", "calories": 1800, "protein": 110},
            {"id": "b", "name": "Ben", "calories": 2400, "protein": 160},
        ],
        "pantry": [],
        "exclude": [],
    })
    assert r.status_code == 200
    body = r.get_json()
    assert body["prefs"]["portions"] == 2
    assert body["prefs"]["calories"] == 2100
    assert body["plan"]["members"][0]["name"] == "Anna"


def test_never_again_and_log_api(client):
    client.post("/api/auth/login", json={"email": "admin@test.local", "password": "testdevpass"})
    client.post("/api/plan", json={
        "store": "Lidl", "diet": "All", "budget": 80, "days": 5,
        "calories": 2000, "protein": 120, "pantry": [], "exclude": [],
    })
    plan = client.get("/api/plan").get_json()["plan"]
    meal = plan["days_plan"][0]["meals"][0]
    logged = client.post("/api/plan/log", json={
        "day_index": 0, "category": meal["category"], "status": "skipped",
    })
    assert logged.status_code == 200
    assert logged.get_json()["plan"]["days_plan"][0]["meals"][0]["status"] == "skipped"
    ban = client.post(f"/api/recipes/{meal['id']}/never-again")
    assert ban.status_code == 200
    ids = client.get("/api/recipes/never-again").get_json()["ids"]
    assert meal["id"] in ids
