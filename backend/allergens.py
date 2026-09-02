ALLERGEN_GROUPS = {
    "Erdnuss": ["Erdnussbutter"],
    "Laktose": [
        "Milch",
        "Magerquark",
        "Naturjoghurt",
        "Joghurt",
        "Feta / Hirtenkäse",
        "Parmesan",
        "Hüttenkäse",
    ],
    "Gluten": ["Haferflocken", "Vollkornpasta", "Vollkornbrot"],
    "Fisch": ["Lachsfilet", "Thunfisch (Dose)"],
    "Ei": ["Eier"],
    "Soja": ["Bio-Tofu", "Sojasauce"],
}

ALLERGEN_OPTIONS = [
    {"id": "Erdnuss", "name": "Erdnuss"},
    {"id": "Laktose", "name": "Laktose / Milch"},
    {"id": "Gluten", "name": "Gluten"},
    {"id": "Fisch", "name": "Fisch"},
    {"id": "Ei", "name": "Ei"},
    {"id": "Soja", "name": "Soja"},
]


def banned_ingredient_names(exclude):
    banned = set()
    for item in exclude or []:
        key = str(item).strip()
        if not key:
            continue
        if key in ALLERGEN_GROUPS:
            banned.update(name.lower() for name in ALLERGEN_GROUPS[key])
        else:
            banned.add(key.lower())
    return banned


def recipe_blocked(recipe, exclude):
    banned = banned_ingredient_names(exclude)
    if not banned:
        return False
    names = {str(name).lower() for name in recipe.get("ingredients", {})}
    return bool(names & banned)
