import json
from pathlib import Path

from backend.extensions import db
from backend.kitchen.catalog import (
    CatalogError,
    create_ingredient,
    create_recipe,
    create_sku,
    current_price,
    map_ingredient_sku,
    record_price,
)
from backend.kitchen.constants import STORES
from backend.kitchen.models import Ingredient, IngredientSku, Recipe, Sku


UNITS = {"g", "ml", "Stück"}

# Typical Lidl / Marktkauf pack + shelf price so imported recipes are shoppable
# until a real Prospekt observation replaces the row.
SHELF = {
    "apple": ("Apfel", "Äpfel 1kg", 1000, "g", "Obst & Gemüse", 1.99, 2.19),
    "banana": ("Banane", "Bananen", 1000, "g", "Obst & Gemüse", 1.29, 1.39),
    "beans": ("Bohnen", "Kidneybohnen 400g", 400, "g", "Vorratskammer & Trocken", 0.69, 0.79),
    "bell-pepper": ("Paprika", "Paprika 500g", 500, "g", "Obst & Gemüse", 1.99, 2.19),
    "bread": ("Brot", "Toastbrot 500g", 500, "g", "Vorratskammer & Trocken", 1.29, 1.39),
    "broccoli": ("Brokkoli", "Brokkoli 500g", 500, "g", "Obst & Gemüse", 1.49, 1.69),
    "bulgur": ("Bulgur", "Bulgur 500g", 500, "g", "Vorratskammer & Trocken", 1.29, 1.49),
    "butter": ("Butter", "Deutsche Markenbutter 250g", 250, "g", "Kühlregal & Molkerei", 1.89, 2.09),
    "cabbage": ("Kohl", "Spitzkohl", 1000, "g", "Obst & Gemüse", 1.19, 1.29),
    "carrot": ("Karotte", "Möhren 1kg", 1000, "g", "Obst & Gemüse", 0.99, 1.09),
    "cheese": ("Käse", "Gouda gerieben 250g", 250, "g", "Kühlregal & Molkerei", 1.99, 2.19),
    "chicken": ("Hähnchen", "Hähnchenbrust 500g", 500, "g", "Fleisch, Fisch & Tofu", 4.49, 4.99),
    "chickpeas": ("Kichererbsen", "Kichererbsen 400g", 400, "g", "Vorratskammer & Trocken", 0.69, 0.79),
    "chili": ("Chili", "Chilipulver 50g", 50, "g", "Vorratskammer & Trocken", 0.79, 0.89),
    "coconut-milk": ("Kokosmilch", "Kokosmilch 400ml", 400, "ml", "Vorratskammer & Trocken", 1.19, 1.29),
    "couscous": ("Couscous", "Couscous 500g", 500, "g", "Vorratskammer & Trocken", 1.19, 1.29),
    "cucumber": ("Gurke", "Salatgurke", 1, "Stück", "Obst & Gemüse", 0.69, 0.79),
    "cumin": ("Kreuzkümmel", "Kreuzkümmel 50g", 50, "g", "Vorratskammer & Trocken", 0.79, 0.89),
    "curry-powder": ("Currypulver", "Currypulver 50g", 50, "g", "Vorratskammer & Trocken", 0.79, 0.89),
    "egg-noodles": ("Eiernudeln", "Eiernudeln 250g", 250, "g", "Vorratskammer & Trocken", 1.19, 1.29),
    "eggs": ("Eier", "Freilandeier 10er", 10, "Stück", "Kühlregal & Molkerei", 2.19, 2.39),
    "feta": ("Feta", "Schafskäse 200g", 200, "g", "Kühlregal & Molkerei", 1.49, 1.69),
    "flour": ("Mehl", "Weizenmehl 1kg", 1000, "g", "Vorratskammer & Trocken", 0.79, 0.89),
    "frozen-berries": ("Beeren TK", "Beerenmischung 300g", 300, "g", "Kühlregal & Tiefkühl", 1.99, 2.19),
    "frozen-peas": ("Erbsen TK", "Erbsen 450g", 450, "g", "Kühlregal & Tiefkühl", 0.99, 1.09),
    "garlic": ("Knoblauch", "Knoblauch 100g", 100, "g", "Obst & Gemüse", 0.69, 0.79),
    "ginger": ("Ingwer", "Ingwer 100g", 100, "g", "Obst & Gemüse", 0.89, 0.99),
    "honey": ("Honig", "Flüssighonig 250g", 250, "g", "Vorratskammer & Trocken", 2.49, 2.79),
    "ketchup": ("Ketchup", "Tomatensauce 500ml", 500, "ml", "Vorratskammer & Trocken", 0.89, 0.99),
    "lemon": ("Zitrone", "Zitrone", 1, "Stück", "Obst & Gemüse", 0.39, 0.45),
    "lentils": ("Linsen", "Rote Linsen 500g", 500, "g", "Vorratskammer & Trocken", 1.29, 1.49),
    "lime": ("Limette", "Limette", 1, "Stück", "Obst & Gemüse", 0.39, 0.45),
    "milk": ("Milch", "Vollmilch 1l", 1000, "ml", "Kühlregal & Molkerei", 1.09, 1.15),
    "minced-beef": ("Hackfleisch", "Rinderhack 500g", 500, "g", "Fleisch, Fisch & Tofu", 3.99, 4.49),
    "mushrooms": ("Pilze", "Champignons 250g", 250, "g", "Obst & Gemüse", 1.29, 1.39),
    "mustard": ("Senf", "Mittelscharfer Senf 250ml", 250, "ml", "Vorratskammer & Trocken", 0.79, 0.89),
    "noodles": ("Nudeln", "Weizennudeln 250g", 250, "g", "Vorratskammer & Trocken", 1.29, 1.39),
    "oats": ("Haferflocken", "Haferflocken 500g", 500, "g", "Vorratskammer & Trocken", 0.89, 1.19),
    "oil": ("Öl", "Rapsöl 500ml", 500, "ml", "Vorratskammer & Trocken", 2.29, 2.49),
    "onion": ("Zwiebel", "Zwiebeln 1kg", 1000, "g", "Obst & Gemüse", 0.99, 1.09),
    "paprika-spice": ("Paprikapulver", "Paprikapulver 50g", 50, "g", "Vorratskammer & Trocken", 0.69, 0.79),
    "pasta": ("Pasta", "Spaghetti 500g", 500, "g", "Vorratskammer & Trocken", 0.79, 0.89),
    "peanut-butter": ("Erdnussbutter", "Erdnussmus 350g", 350, "g", "Vorratskammer & Trocken", 1.79, 1.99),
    "pepper": ("Pfeffer", "Schwarzer Pfeffer 50g", 50, "g", "Vorratskammer & Trocken", 0.89, 0.99),
    "polenta": ("Polenta", "Polenta 500g", 500, "g", "Vorratskammer & Trocken", 1.09, 1.19),
    "potato": ("Kartoffel", "Festkochende Kartoffeln 2kg", 2000, "g", "Obst & Gemüse", 1.79, 1.99),
    "quark": ("Quark", "Magerquark 500g", 500, "g", "Kühlregal & Molkerei", 1.19, 1.29),
    "rice": ("Reis", "Langkornreis 1kg", 1000, "g", "Vorratskammer & Trocken", 1.49, 1.79),
    "salad": ("Salat", "Kopfsalat", 150, "g", "Obst & Gemüse", 0.99, 1.09),
    "salmon": ("Lachs", "Lachsfilet 250g", 250, "g", "Fleisch, Fisch & Tofu", 4.99, 5.49),
    "salt": ("Salz", "Speisesalz 500g", 500, "g", "Vorratskammer & Trocken", 0.49, 0.55),
    "sesame": ("Sesam", "Sesam 100g", 100, "g", "Vorratskammer & Trocken", 1.19, 1.29),
    "soy-sauce": ("Sojasauce", "Sojasauce 250ml", 250, "ml", "Vorratskammer & Trocken", 1.59, 1.89),
    "spinach": ("Spinat", "Blattspinat 200g", 200, "g", "Obst & Gemüse", 1.29, 1.39),
    "stock": ("Brühe", "Gemüsebrühe 1l", 1000, "ml", "Vorratskammer & Trocken", 0.89, 0.99),
    "tamarind": ("Tamarinde", "Tamarindenpaste 200g", 200, "g", "Vorratskammer & Trocken", 2.49, 2.69),
    "tofu": ("Tofu", "Naturtofu 400g", 400, "g", "Fleisch, Fisch & Tofu", 1.49, 1.69),
    "tomato": ("Tomate", "Rispen-Tomaten 500g", 500, "g", "Obst & Gemüse", 1.49, 1.69),
    "tuna": ("Thunfisch", "Thunfisch 150g", 150, "g", "Fleisch, Fisch & Tofu", 1.29, 1.39),
    "vinegar": ("Essig", "Branntweinessig 500ml", 500, "ml", "Vorratskammer & Trocken", 0.69, 0.79),
    "wraps": ("Wraps", "Weizen-Wraps 370g", 370, "g", "Vorratskammer & Trocken", 1.49, 1.69),
    "yogurt": ("Joghurt", "Naturjoghurt 500g", 500, "g", "Kühlregal & Molkerei", 0.79, 0.89),
    "zucchini": ("Zucchini", "Zucchini 500g", 500, "g", "Obst & Gemüse", 1.29, 1.39),
}


def _shelf_spec(ingredient):
    row = SHELF.get(ingredient.id)
    if row:
        de, sku, pack_size, pack_unit, aisle, lidl, mk = row
        return {
            "de": de,
            "sku": sku,
            "pack_size": pack_size,
            "pack_unit": pack_unit,
            "aisle": aisle,
            "lidl": lidl,
            "marktkauf": mk,
        }
    unit = ingredient.default_unit if ingredient.default_unit in UNITS else "g"
    size = 1 if unit == "Stück" else 500
    name = (ingredient.canonical_name or ingredient.id).replace("-", " ")
    return {
        "de": name,
        "sku": name,
        "pack_size": size,
        "pack_unit": unit,
        "aisle": "Sonstiges",
        "lidl": 1.49,
        "marktkauf": 1.69,
    }


def _ean(store, ingredient_id):
    n = 0
    for ch in f"{store}:{ingredient_id}":
        n = (n * 33 + ord(ch)) % 10**10
    prefix = "81" if store == "lidl" else "82"
    return f"{prefix}{n:010d}"


def _ensure_ingredient(ingredient_id, unit):
    existing = db.session.get(Ingredient, ingredient_id)
    if existing is not None:
        return existing
    spec = SHELF.get(ingredient_id)
    de_name = spec[0] if spec else ingredient_id.replace("-", " ")
    canonical = spec[0] if spec else ingredient_id.replace("-", " ")
    unit = unit if unit in UNITS else (spec[3] if spec else "g")
    return create_ingredient(
        ingredient_id,
        canonical,
        unit,
        aliases=[{"locale": "de", "name": de_name}],
    )


def import_recipe_list(payload, publish_if_mapped=False):
    if not isinstance(payload, list):
        raise CatalogError("payload must be a list")
    created = 0
    skipped = 0
    for raw in payload:
        rid = str(raw.get("id") or "").strip()
        if not rid or db.session.get(Recipe, rid):
            skipped += 1
            continue
        for line in raw.get("lines") or []:
            iid = str(line.get("ingredient_id") or "").strip()
            if iid:
                _ensure_ingredient(iid, line.get("unit"))
        try:
            create_recipe(
                rid,
                raw.get("title"),
                slot=raw.get("slot"),
                active_time_minutes=raw.get("active_time_minutes") or 20,
                lines=raw.get("lines") or [],
                steps=raw.get("steps") or [],
                cuisine=raw.get("cuisine") or "international",
                locale=raw.get("locale") or "de",
                servings=raw.get("servings") or 2,
                status="draft",
                diets=raw.get("diets"),
                allergens=raw.get("allergens"),
                macros={
                    "calories": raw.get("calories"),
                    "protein": raw.get("protein"),
                    "carbs": raw.get("carbs"),
                    "fat": raw.get("fat"),
                    "fiber": raw.get("fiber"),
                },
                equipment=raw.get("equipment"),
            )
            db.session.commit()
            created += 1
        except CatalogError:
            skipped += 1
            db.session.rollback()
            continue
    mapped = _auto_map_new_ingredients()
    shelf = _ensure_placeholder_skus()
    published = 0
    if publish_if_mapped:
        published = _publish_fully_mapped()
    return {
        "created": created,
        "skipped": skipped,
        "mapped": mapped,
        "shelf": shelf,
        "published": published,
    }


def _auto_map_new_ingredients():
    count = 0
    for ing in Ingredient.query.all():
        for store in STORES:
            if IngredientSku.query.filter_by(ingredient_id=ing.id, store=store).first():
                continue
            sku = Sku.query.filter_by(store=store).filter(Sku.name.ilike(f"%{ing.canonical_name}%")).first()
            if sku is None:
                continue
            if current_price(sku.id) is None:
                continue
            map_ingredient_sku(ing.id, store, sku.id)
            count += 1
    db.session.commit()
    return count


def _ensure_placeholder_skus():
    count = 0
    for ing in Ingredient.query.all():
        spec = _shelf_spec(ing)
        for store in STORES:
            if IngredientSku.query.filter_by(ingredient_id=ing.id, store=store).first():
                continue
            ean = _ean(store, ing.id)
            sku = Sku.query.filter_by(store=store, ean=ean).first()
            if sku is None:
                sku = create_sku(
                    store,
                    spec["sku"],
                    spec["pack_size"],
                    spec["pack_unit"],
                    aisle=spec["aisle"],
                    ean=ean,
                )
            if current_price(sku.id) is None:
                record_price(
                    sku.id,
                    spec[store],
                    source="import",
                    confidence="medium",
                )
            map_ingredient_sku(ing.id, store, sku.id)
            count += 1
    db.session.commit()
    return count


def _publish_fully_mapped():
    from backend.kitchen.shoppable import unmapped_ingredient_ids

    count = 0
    for recipe in Recipe.query.filter_by(status="draft").all():
        lidl_ok = not unmapped_ingredient_ids(recipe.id, "lidl")
        mk_ok = not unmapped_ingredient_ids(recipe.id, "marktkauf")
        if lidl_ok or mk_ok:
            recipe.status = "published"
            count += 1
    db.session.commit()
    return count


def import_from_path(path, publish_if_mapped=True):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and "recipes" in data:
        data = data["recipes"]
    return import_recipe_list(data, publish_if_mapped=publish_if_mapped)
