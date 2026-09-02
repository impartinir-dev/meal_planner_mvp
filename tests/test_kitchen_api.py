from backend.extensions import db
from backend.kitchen.seed import seed_owned_catalog


def _login(client):
    client.post("/api/auth/login", json={"email": "admin@test.local", "password": "testdevpass"})


def test_stores_never_include_unpriced_chains(client):
    _login(client)
    r = client.get("/api/kitchen/stores")
    assert r.status_code == 200
    ids = {s["id"] for s in r.get_json()["stores"]}
    assert "rewe" not in ids
    assert "REWE" not in ids
    assert ids <= {"lidl", "marktkauf"}


def test_seed_makes_lidl_and_marktkauf_live(client, app):
    with app.app_context():
        seed_owned_catalog()
    _login(client)
    stores = {s["id"] for s in client.get("/api/kitchen/stores").get_json()["stores"]}
    assert stores == {"lidl", "marktkauf"}
    assert "REWE" not in stores
    assert "rewe" not in stores


def test_published_recipes_hide_unshoppable_when_store_set(client, app):
    with app.app_context():
        seed_owned_catalog()
    _login(client)
    lidl = client.get("/api/kitchen/recipes?store=lidl").get_json()["recipes"]
    ids = {r["id"] for r in lidl}
    assert "eggs-on-toast" in ids
    assert "soy-fried-rice" in ids
    assert "pad-thai" not in ids
    mk = {r["id"] for r in client.get("/api/kitchen/recipes?store=marktkauf").get_json()["recipes"]}
    assert "oat-bowl" in mk
    assert "eggs-on-toast" not in mk
    assert "pad-thai" not in mk


def test_ten_minute_filter(client, app):
    with app.app_context():
        seed_owned_catalog()
    _login(client)
    ids = {r["id"] for r in client.get("/api/kitchen/recipes?store=lidl&ten_minute=1").get_json()["recipes"]}
    assert "eggs-on-toast" in ids
    assert "oat-bowl" in ids
    assert "soy-fried-rice" not in ids


def test_draft_not_listed_and_admin_can_create(client, app):
    with app.app_context():
        seed_owned_catalog()
    _login(client)
    created = client.post("/api/kitchen/admin/recipes", json={
        "id": "secret-draft",
        "title": "Not ready",
        "slot": "Abendessen",
        "active_time_minutes": 12,
        "status": "draft",
        "steps": ["Keep this in the kitchen."],
        "lines": [{"ingredient_id": "eggs", "quantity": 2, "unit": "Stück"}],
    })
    assert created.status_code == 201
    listed = {r["id"] for r in client.get("/api/kitchen/recipes").get_json()["recipes"]}
    assert "secret-draft" not in listed
    assert client.get("/api/kitchen/recipes/secret-draft").status_code == 200


def test_non_admin_cannot_write_catalog(client, app):
    from backend.seed import create_invite

    with app.app_context():
        seed_owned_catalog()
        code = create_invite().code
    client.post("/api/auth/register", json={
        "email": "cook@test.local",
        "password": "password1",
        "invite_code": code,
    })
    r = client.post("/api/kitchen/admin/ingredients", json={
        "id": "lime",
        "canonical_name": "lime",
        "default_unit": "Stück",
    })
    assert r.status_code == 403


def test_empty_price_rejected_via_api(client, app):
    with app.app_context():
        seed_owned_catalog()
        from backend.kitchen.models import Sku
        sku_id = Sku.query.filter_by(store="lidl", name="Freilandeier 10er").one().id
    _login(client)
    r = client.post("/api/kitchen/admin/prices", json={"sku_id": sku_id, "amount_eur": None})
    assert r.status_code == 400
