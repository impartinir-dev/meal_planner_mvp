import json
import os
import random
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_json_file(rel_path):
    path = os.path.join(BASE_DIR, rel_path)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

RECIPES = load_json_file('data/recipes.json')
PRICES = load_json_file('data/prices.json')
DEALS = load_json_file('data/deals.json')

AISLE_MAP = {
    "Brokkoli": "Obst & Gemüse",
    "Spinat": "Obst & Gemüse",
    "Karotten": "Obst & Gemüse",
    "Zwiebeln": "Obst & Gemüse",
    "Knoblauch": "Obst & Gemüse",
    "Eisbergsalat": "Obst & Gemüse",
    "Tomaten": "Obst & Gemüse",
    "Cherrytomaten": "Obst & Gemüse",
    "Zucchini": "Obst & Gemüse",
    "Bananen": "Obst & Gemüse",
    "Avocado": "Obst & Gemüse",
    "Paprika-Mix": "Obst & Gemüse",
    "Süßkartoffel": "Obst & Gemüse",
    "Beeren (TK)": "Kühlregal & Tiefkühl",
    "Magerquark": "Kühlregal & Molkerei",
    "Milch": "Kühlregal & Molkerei",
    "Joghurt": "Kühlregal & Molkerei",
    "Naturjoghurt": "Kühlregal & Molkerei",
    "Feta / Hirtenkäse": "Kühlregal & Molkerei",
    "Parmesan": "Kühlregal & Molkerei",
    "Eier": "Kühlregal & Molkerei",
    "Hähnchenbrust": "Fleisch, Fisch & Tofu",
    "Putenbrust": "Fleisch, Fisch & Tofu",
    "Rinderhackfleisch": "Fleisch, Fisch & Tofu",
    "Lachsfilet": "Fleisch, Fisch & Tofu",
    "Thunfisch (Dose)": "Fleisch, Fisch & Tofu",
    "Bio-Tofu": "Fleisch, Fisch & Tofu",
    "Reis": "Vorratskammer & Trocken",
    "Haferflocken": "Vorratskammer & Trocken",
    "Vollkornpasta": "Vorratskammer & Trocken",
    "Rote Linsen": "Vorratskammer & Trocken",
    "Kichererbsen": "Vorratskammer & Trocken",
    "Kidneybohnen": "Vorratskammer & Trocken",
    "passierte Tomaten": "Vorratskammer & Trocken",
    "Gemüsebrühe": "Vorratskammer & Trocken",
    "Olivenöl": "Vorratskammer & Trocken",
    "Sojasauce": "Vorratskammer & Trocken",
    "Erdnussbutter": "Vorratskammer & Trocken",
    "Chia-Samen": "Vorratskammer & Trocken"
}

DAYS_NAMES = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

def get_ingredient_pricing(ingredient, store):
    """
    Returns (effective_price, regular_price, is_deal, deal_badge, discount_percent)
    Price is per 100g or per piece (for eggs/avocado).
    """
    store_deals = DEALS.get(store, [])
    deal_info = next((d for d in store_deals if d['ingredient'].lower() == ingredient.lower()), None)
    
    store_prices = PRICES.get(store, {})
    regular_price = store_prices.get(ingredient, 0.40)
    
    if deal_info:
        return (
            deal_info['offer_price'],
            deal_info['regular_price'],
            True,
            deal_info.get('badge', 'Angebot'),
            deal_info.get('discount_percent', 25)
        )
    return (regular_price, regular_price, False, None, 0)

def evaluate_recipe(recipe, store, pantry_items=None):
    """
    Calculates cost, savings, and deal details for a recipe.
    """
    if pantry_items is None:
        pantry_items = []
    pantry_set = {item.strip().lower() for item in pantry_items}
    
    cost = 0.0
    regular_cost = 0.0
    deal_savings = 0.0
    pantry_savings = 0.0
    deal_items_count = 0
    ingredients_detail = []
    
    for ing, qty in recipe['ingredients'].items():
        eff_price, reg_price, is_deal, badge, discount = get_ingredient_pricing(ing, store)
        is_in_pantry = ing.lower() in pantry_set
        
        # Portion multiplier: for grams it's qty / 100, for piece it's qty
        unit_factor = qty if ing in ["Eier", "Avocado"] else (qty / 100.0)
        
        item_regular = unit_factor * reg_price
        item_discounted = unit_factor * eff_price
        
        if is_in_pantry:
            item_effective = 0.0
            pantry_savings += item_discounted
        else:
            item_effective = item_discounted
            if is_deal:
                deal_savings += (item_regular - item_discounted)
                deal_items_count += 1
        
        cost += item_effective
        regular_cost += item_regular
        
        ingredients_detail.append({
            "name": ing,
            "quantity": qty,
            "unit": "Stück" if ing in ["Eier", "Avocado"] else "g",
            "is_deal": is_deal,
            "deal_badge": badge,
            "discount_percent": discount,
            "in_pantry": is_in_pantry,
            "item_cost": round(item_effective, 2),
            "aisle": AISLE_MAP.get(ing, "Sonstiges")
        })
        
    return {
        "cost": round(cost, 2),
        "regular_cost": round(regular_cost, 2),
        "deal_savings": round(deal_savings, 2),
        "pantry_savings": round(pantry_savings, 2),
        "deal_items_count": deal_items_count,
        "ingredients_detail": ingredients_detail
    }

def get_recipe_score(recipe_eval, recipe, target_protein=140):
    """
    Higher score for:
    - High protein per euro
    - Items on sale (deal bonus)
    - Reasonable calories
    """
    cost = max(recipe_eval['cost'], 0.20)
    protein = recipe['macros']['protein']
    protein_per_euro = (protein / cost) * 10
    deal_bonus = recipe_eval['deal_items_count'] * 8.0
    return protein_per_euro + deal_bonus

def get_recipe_lucide_icon(recipe):
    name = recipe.get('name', '').lower()
    cat = recipe.get('category', '')
    if any(w in name for w in ['shake', 'smoothie', 'becher']):
        return 'cup-soda'
    if any(w in name for w in ['haferflocken', 'oats', 'bowl', 'porridge']):
        return 'coffee'
    if any(w in name for w in ['rührei', 'eier', 'scramble', 'omelett']):
        return 'egg'
    if any(w in name for w in ['lachs', 'thunfisch', 'fisch']):
        return 'fish'
    if any(w in name for w in ['hähnchen', 'pute', 'steak', 'hackfleisch', 'gratin']):
        return 'drumstick'
    if any(w in name for w in ['curry', 'suppe', 'eintopf']):
        return 'soup'
    if any(w in name for w in ['salat']):
        return 'salad'
    if any(w in name for w in ['pasta', 'bolognese', 'chili']):
        return 'utensils'
    if cat == 'Frühstück':
        return 'sun'
    elif cat == 'Mittagessen':
        return 'utensils'
    else:
        return 'moon'

def generate_meal_plan(store="REWE", diet="All", budget=50.0, days=7, target_calories=2200, target_protein=140, pantry=None):
    if pantry is None:
        pantry = []
        
    # 1. Filter by diet
    valid_recipes = []
    for r in RECIPES:
        if diet == "All" or diet in r.get('diets', []):
            valid_recipes.append(r)
            
    if not valid_recipes:
        return {"status": "error", "message": f"Keine Rezepte für Ernährungsform '{diet}' gefunden."}

    # Group by category
    breakfasts = [r for r in valid_recipes if r.get('category') == 'Frühstück']
    lunches = [r for r in valid_recipes if r.get('category') == 'Mittagessen']
    dinners = [r for r in valid_recipes if r.get('category') == 'Abendessen']
    
    # Fallback if any category is empty
    if not breakfasts: breakfasts = valid_recipes
    if not lunches: lunches = valid_recipes
    if not dinners: dinners = valid_recipes

    # Score candidates
    def score_list(recipe_list):
        scored = []
        for r in recipe_list:
            ev = evaluate_recipe(r, store, pantry)
            score = get_recipe_score(ev, r, target_protein)
            scored.append((score, r, ev))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored

    scored_breakfasts = score_list(breakfasts)
    scored_lunches = score_list(lunches)
    scored_dinners = score_list(dinners)

    # Build day by day plan with variety
    days_plan = []
    total_cost = 0.0
    regular_cost = 0.0
    deal_savings = 0.0
    pantry_savings = 0.0
    
    total_cals = 0
    total_prot = 0
    total_carbs = 0
    total_fat = 0
    
    b_idx, l_idx, d_idx = 0, 0, 0
    
    for i in range(days):
        day_name = DAYS_NAMES[i % len(DAYS_NAMES)]
        
        # Pick with slight rotation to keep variety
        b_item = scored_breakfasts[(b_idx + i) % len(scored_breakfasts)]
        l_item = scored_lunches[(l_idx + i) % len(scored_lunches)]
        d_item = scored_dinners[(d_idx + i) % len(scored_dinners)]
        
        day_meals = []
        day_cost = 0.0
        day_cals = 0
        day_prot = 0
        
        for meal_type, (sc, r, ev) in [("Frühstück", b_item), ("Mittagessen", l_item), ("Abendessen", d_item)]:
            day_cost += ev['cost']
            regular_cost += ev['regular_cost']
            deal_savings += ev['deal_savings']
            pantry_savings += ev['pantry_savings']
            
            day_cals += r['macros']['calories']
            day_prot += r['macros']['protein']
            total_carbs += r['macros']['carbs']
            total_fat += r['macros']['fat']
            
            day_meals.append({
                "id": r['id'],
                "name": r['name'],
                "category": meal_type,
                "prep_time": r.get('prep_time', '15 Min'),
                "icon": r.get('icon', '🍽️'),
                "lucide_icon": get_recipe_lucide_icon(r),
                "cost": ev['cost'],
                "regular_cost": ev['regular_cost'],
                "deal_savings": ev['deal_savings'],
                "has_deal": ev['deal_items_count'] > 0,
                "macros": r['macros'],
                "ingredients": ev['ingredients_detail'],
                "instructions": r['instructions']
            })
            
        total_cost += day_cost
        total_cals += day_cals
        total_prot += day_prot
        
        days_plan.append({
            "day_index": i,
            "day_name": day_name,
            "cost": round(day_cost, 2),
            "calories": day_cals,
            "protein": day_prot,
            "meals": day_meals
        })

    # If over budget, adjust by swapping expensive meals to budget-friendly recipes
    if total_cost > budget:
        cheapest_breakfasts = sorted(scored_breakfasts, key=lambda x: x[2]['cost'])
        cheapest_dinners = sorted(scored_dinners, key=lambda x: x[2]['cost'])
        
        for day in days_plan:
            if total_cost <= budget:
                break
            # try swap dinner or breakfast
            old_dinner = day['meals'][2]
            cheap_rep = cheapest_dinners[0]
            if cheap_rep[2]['cost'] < old_dinner['cost']:
                diff = old_dinner['cost'] - cheap_rep[2]['cost']
                total_cost -= diff
                day['meals'][2] = {
                    "id": cheap_rep[1]['id'],
                    "name": cheap_rep[1]['name'],
                    "category": "Abendessen",
                    "prep_time": cheap_rep[1].get('prep_time', '15 Min'),
                    "icon": cheap_rep[1].get('icon', '🍽️'),
                    "lucide_icon": get_recipe_lucide_icon(cheap_rep[1]),
                    "cost": cheap_rep[2]['cost'],
                    "regular_cost": cheap_rep[2]['regular_cost'],
                    "deal_savings": cheap_rep[2]['deal_savings'],
                    "has_deal": cheap_rep[2]['deal_items_count'] > 0,
                    "macros": cheap_rep[1]['macros'],
                    "ingredients": cheap_rep[2]['ingredients_detail'],
                    "instructions": cheap_rep[1]['instructions']
                }

    # Build Shopping List aggregated by supermarket aisles
    shopping_dict = defaultdict(lambda: {
        "quantity": 0,
        "unit": "g",
        "is_deal": False,
        "deal_badge": None,
        "in_pantry": False,
        "aisle": "Sonstiges",
        "estimated_cost": 0.0
    })

    for day in days_plan:
        for meal in day['meals']:
            for ing in meal['ingredients']:
                key = ing['name']
                item = shopping_dict[key]
                item['quantity'] += ing['quantity']
                item['unit'] = ing['unit']
                item['aisle'] = ing['aisle']
                if ing['is_deal']:
                    item['is_deal'] = True
                    item['deal_badge'] = ing['deal_badge']
                if ing['in_pantry']:
                    item['in_pantry'] = True
                item['estimated_cost'] += ing['item_cost']

    shopping_by_aisle = defaultdict(list)
    for name, data in shopping_dict.items():
        shopping_by_aisle[data['aisle']].append({
            "name": name,
            "quantity": data['quantity'],
            "unit": data['unit'],
            "is_deal": data['is_deal'],
            "deal_badge": data['deal_badge'],
            "in_pantry": data['in_pantry'],
            "cost": round(data['estimated_cost'], 2)
        })

    # Sort items within each aisle
    aisle_order = ["Obst & Gemüse", "Kühlregal & Molkerei", "Kühlregal & Tiefkühl", "Fleisch, Fisch & Tofu", "Vorratskammer & Trocken", "Sonstiges"]
    ordered_shopping_list = []
    for aisle in aisle_order:
        if aisle in shopping_by_aisle:
            ordered_shopping_list.append({
                "aisle": aisle,
                "items": sorted(shopping_by_aisle[aisle], key=lambda x: x['name'])
            })

    total_cost = round(total_cost, 2)
    regular_cost = round(regular_cost, 2)
    deal_savings = round(deal_savings, 2)
    pantry_savings = round(pantry_savings, 2)
    combined_savings = round(max(0.0, (regular_cost + pantry_savings) - total_cost), 2)

    return {
        "status": "success",
        "store": store,
        "diet": diet,
        "days": days,
        "budget": budget,
        "target_calories": target_calories,
        "target_protein": target_protein,
        "total_cost": total_cost,
        "regular_cost": regular_cost,
        "deal_savings": deal_savings,
        "pantry_savings": pantry_savings,
        "combined_savings": combined_savings,
        "budget_percent": min(100, round((total_cost / budget) * 100)) if budget > 0 else 0,
        "daily_avg": {
            "calories": round(total_cals / days),
            "protein": round(total_prot / days),
            "carbs": round(total_carbs / days),
            "fat": round(total_fat / days)
        },
        "days_plan": days_plan,
        "shopping_list": ordered_shopping_list,
        "pantry_items": pantry
    }

def swap_single_meal(day_index, category, current_id, store, diet, pantry):
    """
    Returns an alternative recipe for a specific meal category.
    """
    valid = [r for r in RECIPES if (diet == 'All' or diet in r.get('diets', [])) and r.get('category') == category and r['id'] != current_id]
    if not valid:
        valid = [r for r in RECIPES if r.get('category') == category and r['id'] != current_id]
    if not valid:
        return None
        
    chosen = random.choice(valid)
    ev = evaluate_recipe(chosen, store, pantry)
    
    return {
        "id": chosen['id'],
        "name": chosen['name'],
        "category": category,
        "prep_time": chosen.get('prep_time', '15 Min'),
        "icon": chosen.get('icon', '🍽️'),
        "lucide_icon": get_recipe_lucide_icon(chosen),
        "cost": ev['cost'],
        "regular_cost": ev['regular_cost'],
        "deal_savings": ev['deal_savings'],
        "has_deal": ev['deal_items_count'] > 0,
        "macros": chosen['macros'],
        "ingredients": ev['ingredients_detail'],
        "instructions": chosen['instructions']
    }