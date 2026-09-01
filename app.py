from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json
import os
import uuid
from algorithm import generate_meal_plan, swap_single_meal, DEALS, PRICES, RECIPES

app = Flask(__name__)
app.secret_key = 'nutrimatch_session_secure_2026'

STORES = [
    {"id": "REWE", "name": "REWE", "badge": "Supermarkt", "logo_char": "R"},
    {"id": "Lidl", "name": "Lidl", "badge": "Discounter", "logo_char": "L"},
    {"id": "ALDI Süd", "name": "ALDI Süd", "badge": "Discounter", "logo_char": "A"},
    {"id": "Kaufland", "name": "Kaufland", "badge": "SB-Warenhaus", "logo_char": "K"},
    {"id": "EDEKA", "name": "EDEKA", "badge": "Supermarkt", "logo_char": "E"}
]

DIETS = [
    {"id": "All", "name": "Flexitarisch", "icon": "utensils", "desc": "Ausgewogen & vielseitig"},
    {"id": "High-Protein", "name": "High-Protein", "icon": "dumbbell", "desc": "Maximaler Muskelaufbau"},
    {"id": "Vegetarisch", "name": "Vegetarisch", "icon": "salad", "desc": "Ohne Fleisch & Fisch"},
    {"id": "Vegan", "name": "100% Vegan", "icon": "sprout", "desc": "Rein pflanzlich"},
    {"id": "Low-Carb", "name": "Low-Carb", "icon": "flame", "desc": "Wenig Kohlenhydrate"},
    {"id": "Clean", "name": "Clean Eating", "icon": "sparkles", "desc": "Frisch & unverarbeitet"},
    {"id": "Sparfuchs", "name": "Sparfuchs", "icon": "coins", "desc": "Günstigste Sättigung"}
]

PANTRY_STAPLES = [
    {"name": "Olivenöl", "icon": "droplet", "hint": "Spart ~0,95 €"},
    {"name": "Reis", "icon": "wheat", "hint": "Spart ~0,48 €"},
    {"name": "Haferflocken", "icon": "coffee", "hint": "Spart ~0,32 €"},
    {"name": "Sojasauce", "icon": "flask-conical", "hint": "Spart ~0,45 €"},
    {"name": "Zwiebeln", "icon": "circle-dot", "hint": "Spart ~0,25 €"},
    {"name": "Knoblauch", "icon": "sparkle", "hint": "Spart ~0,20 €"},
    {"name": "Gemüsebrühe", "icon": "soup", "hint": "Spart ~0,18 €"},
    {"name": "Chia-Samen", "icon": "sprout", "hint": "Spart ~0,40 €"},
    {"name": "Erdnussbutter", "icon": "heart", "hint": "Spart ~0,50 €"}
]

ACTIVE_PLANS = {}
ACTIVE_PREFS = {}

def get_session_id():
    if 'sid' not in session:
        session['sid'] = uuid.uuid4().hex
    return session['sid']

def get_or_create_plan():
    sid = get_session_id()
    if sid not in ACTIVE_PLANS:
        plan = generate_meal_plan(
            store="Lidl",
            diet="High-Protein",
            budget=50.0,
            days=7,
            target_calories=2200,
            target_protein=140,
            pantry=["Olivenöl", "Reis", "Haferflocken"]
        )
        ACTIVE_PLANS[sid] = plan
        ACTIVE_PREFS[sid] = {
            'store': 'Lidl',
            'diet': 'High-Protein',
            'budget': 50.0,
            'days': 7,
            'pantry': ["Olivenöl", "Reis", "Haferflocken"]
        }
    return ACTIVE_PLANS[sid]

@app.route('/')
def setup():
    sid = get_session_id()
    prefs = ACTIVE_PREFS.get(sid, {
        'store': 'Lidl',
        'diet': 'High-Protein',
        'budget': 50.0,
        'days': 7,
        'calories': 2200,
        'protein': 140,
        'pantry': ["Olivenöl", "Reis", "Haferflocken"]
    })
    return render_template('setup.html',
                           stores=STORES,
                           diets=DIETS,
                           pantry_staples=PANTRY_STAPLES,
                           current_store=prefs.get('store', 'Lidl'),
                           current_diet=prefs.get('diet', 'High-Protein'),
                           current_budget=prefs.get('budget', 50.0),
                           current_days=prefs.get('days', 7),
                           current_calories=prefs.get('calories', 2200),
                           current_protein=prefs.get('protein', 140),
                           current_pantry=prefs.get('pantry', []))

@app.route('/setup', methods=['POST'])
def handle_setup():
    sid = get_session_id()
    store = request.form.get('store', 'Lidl')
    diet = request.form.get('diet', 'High-Protein')
    budget = float(request.form.get('budget', 50.0))
    days = int(request.form.get('days', 7))
    calories = int(request.form.get('calories', 2200))
    protein = int(request.form.get('protein', 140))
    pantry = request.form.getlist('pantry')

    plan = generate_meal_plan(
        store=store,
        diet=diet,
        budget=budget,
        days=days,
        target_calories=calories,
        target_protein=protein,
        pantry=pantry
    )

    ACTIVE_PLANS[sid] = plan
    ACTIVE_PREFS[sid] = {
        'store': store,
        'diet': diet,
        'budget': budget,
        'days': days,
        'calories': calories,
        'protein': protein,
        'pantry': pantry
    }

    return redirect(url_for('view_plan'))

@app.route('/plan')
def view_plan():
    plan = get_or_create_plan()
    return render_template('plan.html', plan=plan)

@app.route('/einkaufszettel')
def view_einkaufszettel():
    plan = get_or_create_plan()
    return render_template('einkaufszettel.html', plan=plan)

@app.route('/api/swap-meal', methods=['POST'])
def api_swap_meal():
    sid = get_session_id()
    data = request.get_json() or {}
    day_index = int(data.get('day_index', 0))
    category = data.get('category', 'Mittagessen')
    current_id = data.get('current_id', '')
    store = data.get('store', 'Lidl')
    diet = data.get('diet', 'All')
    pantry = data.get('pantry', [])

    swapped = swap_single_meal(day_index, category, current_id, store, diet, pantry)
    if not swapped:
        return jsonify({"status": "error", "message": "Keine alternative Mahlzeit gefunden."}), 404

    # Update in-memory plan
    plan = ACTIVE_PLANS.get(sid)
    if plan and 'days_plan' in plan and len(plan['days_plan']) > day_index:
        meals = plan['days_plan'][day_index].get('meals', [])
        for i, m in enumerate(meals):
            if m.get('id') == current_id:
                meals[i] = swapped
                break
        ACTIVE_PLANS[sid] = plan

    return jsonify({"status": "success", "meal": swapped})

if __name__ == '__main__':
    app.run(debug=True, port=5000)