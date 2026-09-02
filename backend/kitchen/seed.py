from backend.extensions import db
from backend.kitchen.catalog import (
    create_ingredient,
    create_recipe,
    create_sku,
    map_ingredient_sku,
    record_offer,
    record_price,
)
from backend.kitchen.models import Ingredient


def seed_owned_catalog():
    """Small house catalog for Lidl + Marktkauf fixtures. Idempotent."""
    if Ingredient.query.filter_by(id="eggs").first() is not None:
        return

    create_ingredient("eggs", "eggs", "Stück", [{"locale": "de", "name": "Eier"}])
    create_ingredient("bread", "bread", "g", [{"locale": "de", "name": "Toastbrot"}])
    create_ingredient("rice", "rice", "g", [{"locale": "de", "name": "Reis"}])
    create_ingredient("soy-sauce", "soy sauce", "ml", [{"locale": "de", "name": "Sojasauce"}])
    create_ingredient("tamarind", "tamarind", "g", [{"locale": "de", "name": "Tamarinde"}])
    create_ingredient("oats", "oats", "g", [{"locale": "de", "name": "Haferflocken"}])
    create_ingredient("milk", "milk", "ml", [{"locale": "de", "name": "Milch"}])

    lidl_eggs = create_sku("lidl", "Freilandeier 10er", 10, "Stück", aisle="Kühlregal & Molkerei", ean="400000000001")
    lidl_bread = create_sku("lidl", "Toastbrot 500g", 500, "g", aisle="Vorratskammer & Trocken", ean="400000000002")
    lidl_rice = create_sku("lidl", "Langkornreis 1kg", 1000, "g", aisle="Vorratskammer & Trocken", ean="400000000003")
    lidl_soy = create_sku("lidl", "Sojasauce 250ml", 250, "ml", aisle="Vorratskammer & Trocken", ean="400000000004")
    lidl_oats = create_sku("lidl", "Haferflocken 500g", 500, "g", aisle="Vorratskammer & Trocken", ean="400000000005")
    lidl_milk = create_sku("lidl", "Vollmilch 1l", 1000, "ml", aisle="Kühlregal & Molkerei", ean="400000000006")

    mk_eggs = create_sku("marktkauf", "Eier 10er", 10, "Stück", aisle="Kühlregal & Molkerei", ean="500000000001")
    mk_oats = create_sku("marktkauf", "Kernige Haferflocken 1kg", 1000, "g", aisle="Vorratskammer & Trocken", ean="500000000002")
    mk_milk = create_sku("marktkauf", "Frischmilch 1l", 1000, "ml", aisle="Kühlregal & Molkerei", ean="500000000003")
    mk_rice = create_sku("marktkauf", "Langkornreis 1kg", 1000, "g", aisle="Vorratskammer & Trocken", ean="500000000004")
    mk_soy = create_sku("marktkauf", "Sojasauce 250ml", 250, "ml", aisle="Vorratskammer & Trocken", ean="500000000005")

    record_price(lidl_eggs.id, 2.19)
    record_price(lidl_bread.id, 1.29)
    record_price(lidl_rice.id, 1.49)
    record_price(lidl_soy.id, 1.59)
    record_price(lidl_oats.id, 0.89)
    record_price(lidl_milk.id, 1.09)
    record_offer(lidl_eggs.id, "2026-W36", 1.79, regular_price=2.19, badge="Prospekt-Knaller")
    record_offer(lidl_oats.id, "2026-W36", 0.69, regular_price=0.89, badge="Angebot")

    record_price(mk_eggs.id, 2.39)
    record_price(mk_oats.id, 1.19)
    record_price(mk_milk.id, 1.15)
    record_price(mk_rice.id, 1.79)
    record_price(mk_soy.id, 1.89)

    map_ingredient_sku("eggs", "lidl", lidl_eggs.id)
    map_ingredient_sku("bread", "lidl", lidl_bread.id)
    map_ingredient_sku("rice", "lidl", lidl_rice.id)
    map_ingredient_sku("soy-sauce", "lidl", lidl_soy.id)
    map_ingredient_sku("oats", "lidl", lidl_oats.id)
    map_ingredient_sku("milk", "lidl", lidl_milk.id)
    map_ingredient_sku("eggs", "marktkauf", mk_eggs.id)
    map_ingredient_sku("oats", "marktkauf", mk_oats.id)
    map_ingredient_sku("milk", "marktkauf", mk_milk.id)
    map_ingredient_sku("rice", "marktkauf", mk_rice.id)
    map_ingredient_sku("soy-sauce", "marktkauf", mk_soy.id)

    create_recipe(
        "eggs-on-toast",
        "Rührei auf Toast",
        slot="Frühstück",
        active_time_minutes=8,
        cuisine="international",
        status="published",
        diets=["Vegetarisch", "High-Protein"],
        steps=[
            "Toast toasten.",
            "Eier verquirlen, in der Pfanne cremig stocken.",
            "Auf dem Toast anrichten.",
        ],
        lines=[
            {"ingredient_id": "eggs", "quantity": 3, "unit": "Stück"},
            {"ingredient_id": "bread", "quantity": 70, "unit": "g"},
        ],
        macros={"calories": 380, "protein": 22, "carbs": 28, "fat": 18, "fiber": 2},
    )
    create_recipe(
        "oat-bowl",
        "Haferflocken mit Milch",
        slot="Frühstück",
        active_time_minutes=5,
        cuisine="international",
        status="published",
        diets=["Vegetarisch"],
        steps=["Haferflocken mit Milch aufkochen.", "1 Minute ziehen lassen."],
        lines=[
            {"ingredient_id": "oats", "quantity": 80, "unit": "g"},
            {"ingredient_id": "milk", "quantity": 200, "unit": "ml"},
        ],
        macros={"calories": 320, "protein": 14, "carbs": 48, "fat": 8, "fiber": 6},
    )
    create_recipe(
        "soy-fried-rice",
        "Soy fried rice",
        slot="Mittagessen",
        active_time_minutes=15,
        cuisine="east-asian",
        locale="en",
        status="published",
        diets=["Vegetarisch"],
        steps=["Cook leftover rice hot in a pan.", "Season with soy sauce.", "Optional fried egg on top."],
        lines=[
            {"ingredient_id": "rice", "quantity": 150, "unit": "g"},
            {"ingredient_id": "soy-sauce", "quantity": 20, "unit": "ml"},
            {"ingredient_id": "eggs", "quantity": 1, "unit": "Stück"},
        ],
        macros={"calories": 520, "protein": 18, "carbs": 78, "fat": 12, "fiber": 2},
    )
    create_recipe(
        "savory-soy-eggs",
        "Soja-Rührei",
        slot="Abendessen",
        active_time_minutes=10,
        cuisine="east-asian",
        status="published",
        diets=["Vegetarisch", "High-Protein"],
        steps=["Eier verquirlen.", "In der Pfanne stocken, mit Sojasauce würzen."],
        lines=[
            {"ingredient_id": "eggs", "quantity": 3, "unit": "Stück"},
            {"ingredient_id": "soy-sauce", "quantity": 15, "unit": "ml"},
        ],
        macros={"calories": 280, "protein": 20, "carbs": 2, "fat": 20, "fiber": 0},
    )
    create_recipe(
        "pad-thai",
        "Pad Thai",
        slot="Abendessen",
        active_time_minutes=25,
        cuisine="thai",
        locale="en",
        status="published",
        steps=["Soak noodles.", "Stir-fry with tamarind sauce.", "Serve with lime."],
        lines=[
            {"ingredient_id": "eggs", "quantity": 2, "unit": "Stück"},
            {"ingredient_id": "tamarind", "quantity": 30, "unit": "g"},
        ],
        macros={"calories": 620, "protein": 28, "carbs": 80, "fat": 18, "fiber": 4},
    )
    db.session.commit()
