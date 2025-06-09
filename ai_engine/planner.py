import math
import json
from .openai_client import get_diet_plan_via_gpt


def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """
    Calculate Basal Metabolic Rate using Mifflin-St Jeor Equation.
    """
    gender = gender.lower()
    if gender == 'male':
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161


def get_activity_multiplier(activity: str) -> float:
    """
    Map user-reported activity level to multiplier.
    """
    mapping = {
        '1': 1.2, '2': 1.375, '3': 1.55, '4': 1.725, '5': 1.9,
        'sedentary': 1.2, 'lightly active': 1.375,
        'moderately active': 1.55, 'very active': 1.725,
        'extra active': 1.9
    }
    key = activity.strip().lower()
    return mapping.get(key, 1.375)


def calculate_tdee(bmr: float, activity: str) -> float:
    """
    Calculate Total Daily Energy Expenditure.
    """
    multiplier = get_activity_multiplier(activity)
    return bmr * multiplier


def adjust_calories(tdee: float, goal: str, conditions: list) -> float:
    """
    Adjust TDEE based on user goal and any health conditions.
    """
    goal = goal.lower()
    # baseline adjustments
    if goal == 'fat loss':
        pct = -0.20
    elif goal == 'muscle gain':
        pct = +0.15
    elif goal == 'weight gain':
        pct = +0.20
    else:
        pct = 0.0
    # mild adjustments for specific conditions
    for cond in conditions:
        c = cond.strip().lower()
        if c in ['diabetes', 'pcos'] and pct < 0:
            pct = max(pct, -0.10)
    return round(tdee * (1 + pct))


def calculate_macros(calories: float, goal: str, conditions: list) -> dict:
    """
    Allocate macros (g) based on total calories and goal/conditions.
    """
    # default ratios
    ratios = {
        'general wellness': (0.40, 0.30, 0.30),
        'fat loss':        (0.35, 0.40, 0.25),
        'muscle gain':     (0.40, 0.35, 0.25),
        'weight gain':     (0.45, 0.25, 0.30)
    }
    key = goal.strip().lower()
    carb_pct, protein_pct, fat_pct = ratios.get(key, ratios['general wellness'])
    # overrides for conditions
    for cond in conditions:
        c = cond.strip().lower()
        if c == 'diabetes':
            carb_pct, protein_pct, fat_pct = 0.30, 0.35, 0.35
        if c == 'pcos':
            carb_pct, protein_pct, fat_pct = 0.30, 0.30, 0.40
        if c in ['thyroid', 'hypothyroidism']:
            carb_pct, protein_pct, fat_pct = 0.35, 0.30, 0.35
    # grams: protein & carb = 4 kcal/g, fat = 9 kcal/g
    grams = {
        'Carbs':    round((calories * carb_pct) / 4),
        'Protein':  round((calories * protein_pct) / 4),
        'Fats':     round((calories * fat_pct) / 9)
    }
    return grams


def build_prompt_payload(user_data: dict, computed: dict) -> dict:
    """
    Merge user inputs and computed metrics into one payload for GPT.
    """
    payload = {
        'user_profile': user_data,
        'computed_metrics': computed
    }
    return payload


def generate_plan(user_data: dict) -> dict:
    """
    Pipeline:
      1. Parse and compute BMR, TDEE, calorie goal, macros
      2. Build prompt payload
      3. Invoke GPT via openai_client
      4. Return parsed plan
    """
    # Extract numeric fields
    weight, height = map(float, user_data.get('Weight & Height', '0kg,0cm')
                         .replace('kg','').replace('cm','').split(','))
    age = int(user_data.get('Age', 30))
    gender = user_data.get('Gender', 'Male')
    activity = user_data.get('Activity level', '2')
    goal = user_data.get('Goals', 'General Wellness')
    conditions = user_data.get('Any food allergies', '').split(',')
    # 1. compute metrics
    bmr = calculate_bmr(weight, height, age, gender)
    tdee = calculate_tdee(bmr, activity)
    calories = adjust_calories(tdee, goal, conditions)
    macros = calculate_macros(calories, goal, conditions)
    computed = {
        'BMR':    round(bmr),
        'TDEE':   round(tdee),
        'CalorieGoal': f"{calories} kcal/day",
        'Macros': macros
    }
    # 2. payload
    payload = build_prompt_payload(user_data, computed)
    # 3. GPT call
    plan = get_diet_plan_via_gpt(payload)
    return plan
