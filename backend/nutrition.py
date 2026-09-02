ACTIVITY = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very": 1.9,
}

GOAL_KCAL = {
    "lose": -400,
    "maintain": 0,
    "gain": 350,
}

PROTEIN_G_PER_KG = {
    "lose": 1.8,
    "maintain": 1.6,
    "gain": 2.0,
}


def calculate_needs(sex, age, height_cm, weight_kg, activity="moderate", goal="maintain"):
    """Mifflin-St Jeor BMR + activity + goal. Protein from bodyweight."""
    try:
        age = int(age)
        height_cm = float(height_cm)
        weight_kg = float(weight_kg)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_numbers") from exc
    if age < 14 or age > 90 or height_cm < 120 or height_cm > 230 or weight_kg < 35 or weight_kg > 250:
        raise ValueError("out_of_range")
    sex = str(sex or "female").lower()
    if sex in ("m", "male", "mann"):
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    factor = ACTIVITY.get(str(activity), 1.55)
    tdee = bmr * factor
    calories = tdee + GOAL_KCAL.get(str(goal), 0)
    calories = int(round(max(1400, min(4000, calories)) / 50.0) * 50)
    prot_per_kg = PROTEIN_G_PER_KG.get(str(goal), 1.6)
    if activity in ("sedentary",) and goal == "maintain":
        prot_per_kg = 1.2
    protein = int(round(max(60, min(240, weight_kg * prot_per_kg)) / 5.0) * 5)
    return {
        "bmr": int(round(bmr)),
        "tdee": int(round(tdee)),
        "calories": calories,
        "protein": protein,
        "activity": activity if activity in ACTIVITY else "moderate",
        "goal": goal if goal in GOAL_KCAL else "maintain",
    }
