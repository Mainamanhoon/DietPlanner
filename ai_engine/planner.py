# ai_engine/planner.py

import json
from ai_engine.openai_client import get_diet_plan_via_gpt

def parse_weight_height(s: str):
    # expects "60kg, 165cm"
    w_str, h_str = s.split(",")
    weight = float(w_str.strip().lower().replace("kg", ""))
    height = float(h_str.strip().lower().replace("cm", ""))
    return weight, height

def calculate_bmr(weight: float, height: float, age: int, gender: str) -> float:
    if gender.lower() == "male":
        return 10*weight + 6.25*height - 5*age + 5
    else:
        return 10*weight + 6.25*height - 5*age - 161

def normalize_activity_level(activity):
    """Convert numeric or string activity level to standard string format"""
    if isinstance(activity, (int, float)) or (isinstance(activity, str) and activity.isdigit()):
        # Convert numeric scale (1-10) to activity categories
        activity_num = int(float(activity))
        if activity_num <= 2:
            return "Sedentary"
        elif activity_num <= 4:
            return "Lightly active"
        elif activity_num <= 6:
            return "Moderately active"
        elif activity_num <= 8:
            return "Very active"
        else:
            return "Extra active"
    
    # Handle string inputs
    activity_str = str(activity).lower()
    if "sedentary" in activity_str or "inactive" in activity_str:
        return "Sedentary"
    elif "lightly" in activity_str or "light" in activity_str:
        return "Lightly active"
    elif "moderately" in activity_str or "moderate" in activity_str:
        return "Moderately active"
    elif "very" in activity_str or "highly" in activity_str:
        return "Very active"
    elif "extra" in activity_str or "extremely" in activity_str:
        return "Extra active"
    else:
        # Default fallback
        return "Lightly active"

def calculate_tdee(bmr: float, activity: str) -> float:
    factors = {
        "Sedentary": 1.2,
        "Lightly active": 1.375,
        "Moderately active": 1.55,
        "Very active": 1.725,
        "Extra active": 1.9
    }
    return bmr * factors.get(activity, 1.375)

def adjust_calories(tdee: float, goal: str) -> float:
    goal = goal.lower()
    if goal == "fat loss":
        return tdee * 0.8      # 20% deficit
    if goal == "muscle gain":
        return tdee * 1.15     # 15% surplus
    if goal == "weight gain":
        return tdee * 1.20     # 20% surplus
    return tdee               # general wellness

def compute_macros(calories: float, goal: str) -> dict:
    # ratios by goal
    ratios = {
        "fat loss":       {"protein":0.40, "carbs":0.35, "fats":0.25},
        "muscle gain":    {"protein":0.35, "carbs":0.40, "fats":0.25},
        "weight gain":    {"protein":0.25, "carbs":0.45, "fats":0.30},
        "general wellness":{"protein":0.30,"carbs":0.40, "fats":0.30}
    }
    goal_key = goal.lower()
    r = ratios.get(goal_key, ratios["general wellness"])
    # 1g protein or carb = 4 kcal, fat = 9 kcal
    return {
        "Protein_g": round((calories * r["protein"]) / 4, 1),
        "Carbs_g":   round((calories * r["carbs"])   / 4, 1),
        "Fats_g":    round((calories * r["fats"])    / 9, 1)
    }

def generate_plan(user_data: dict) -> dict:
    # 1) Parse
    w, h = parse_weight_height(user_data["Weight & Height"])
    age    = int(user_data["Age"])
    gender = user_data["Gender"]
    activity_raw = user_data["Activity level"]
    activity = normalize_activity_level(activity_raw)
    goal = user_data["Goals"]

    print(f"Parsed activity level: '{activity_raw}' -> '{activity}'")

    # 2) Compute
    bmr  = calculate_bmr(w, h, age, gender)
    tdee = calculate_tdee(bmr, activity)
    cal_goal = adjust_calories(tdee, goal)
    macros   = compute_macros(cal_goal, goal)

    print(f"BMR: {bmr:.0f}, TDEE: {tdee:.0f}, Calorie Goal: {cal_goal:.0f}")

    # 3) Build payload
    payload = {
        "user_profile": user_data,
        "calorie_goal": f"{round(cal_goal)} kcal/day",
        "macros": macros
    }

    # 4) Call GPT
    return get_diet_plan_via_gpt(payload)