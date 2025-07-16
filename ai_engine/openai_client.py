import os
import json
import openai
import pandas as pd
import time
import random
from dotenv import load_dotenv
from json import JSONDecodeError

# ─── 1. Load your API key ────────────────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in your .env file")
openai.api_key = API_KEY

# ─── 2. Load Indian Cuisine Database ─────────────────────────────────────────
def load_cuisine_database(csv_path="samples/CuisineList.csv"):
    """
    Load the Indian cuisine database from CSV file
    Expected columns: Name, State/Region, Quantity, Calories (kcal), Protein (g), Carbs (g), Fat (g), Veg/Non-Veg, Meal Type, Ingredients
    """
    try:
        df = pd.read_csv(csv_path)
        print(f"Loaded {len(df)} dishes from cuisine database")
        return df
    except FileNotFoundError:
        print(f"Warning: {csv_path} not found. Using fallback dish generation.")
        return None
    except Exception as e:
        print(f"Error loading cuisine database: {e}")
        return None

def filter_dishes_by_preferences(df, diet_type, meal_type=None, region=None, health_conditions=None, dislikes=None, lab_values=None):
    """
    ENHANCED filtering based on user's dietary preferences, health conditions, dislikes, and regional preferences
    This function does ALL the filtering BEFORE creating compact dishes
    """
    if df is None:
        return pd.DataFrame()
    
    filtered = df.copy()
    
    # 1. Filter by diet type
    if diet_type.lower() == "vegetarian":
        filtered = filtered[filtered['Veg/Non-Veg'].str.lower() == 'veg']
    elif diet_type.lower() == "eggetarian":
        filtered = filtered[filtered['Veg/Non-Veg'].str.lower().isin(['veg', 'eggetarian'])]
    elif diet_type.lower() == "non-vegetarian":
        filtered = filtered  # All dishes allowed
    elif diet_type.lower() == "jain":
        # Jain diet - only veg dishes, exclude root vegetables
        filtered = filtered[filtered['Veg/Non-Veg'].str.lower() == 'veg']
        # Filter out dishes with root vegetables (onion, garlic, potato, etc.)
        jain_exclude_ingredients = ['onion', 'garlic', 'potato', 'carrot', 'radish', 'beetroot', 'ginger']
        for ingredient in jain_exclude_ingredients:
            filtered = filtered[~filtered['Ingredients'].str.lower().str.contains(ingredient, na=False)]
    
    # 2. Filter by meal type if specified (FIXED to handle "Lunch/Dinner" format)
    if meal_type:
        meal_type_lower = meal_type.lower()
        # Split meal types by '/' and check if our target meal type is in any of them
        def contains_meal_type(meal_type_str):
            if pd.isna(meal_type_str):
                return False
            # Split by '/' and check each part
            meal_parts = [part.strip().lower() for part in str(meal_type_str).split('/')]
            return meal_type_lower in meal_parts
        
        filtered = filtered[filtered['Meal Type'].apply(contains_meal_type)]
    
    # 3. Filter by regional preference
    if region and region.lower() != "mixed" and region.lower() != "both":
        if "north" in region.lower():
            filtered = filtered[filtered['State/Region'].str.lower().str.contains('north|punjab|delhi|haryana|uttar pradesh|pan-india|universal', na=False)]
        elif "south" in region.lower():
            filtered = filtered[filtered['State/Region'].str.lower().str.contains('south|tamil nadu|karnataka|kerala|andhra|telangana|pan-india|universal', na=False)]
        elif "western" in region.lower():
            filtered = filtered[filtered['State/Region'].str.lower().str.contains('western|maharashtra|gujarat|goa|rajasthan|pan-india|universal', na=False)]
        elif "eastern" in region.lower():
            filtered = filtered[filtered['State/Region'].str.lower().str.contains('eastern|west bengal|odisha|assam|bihar|jharkhand|pan-india|universal', na=False)]
    
    # 4. Filter by health conditions (COMPREHENSIVE)
    if health_conditions:
        for condition in health_conditions:
            condition_lower = condition.lower()
            
            if condition_lower == "diabetes":
                # Exclude high-GI foods, sweets, refined carbs
                diabetes_exclude = ['sweet', 'sugar', 'jaggery', 'refined flour', 'white rice', 'bhature', 'jalebi', 'laddu', 'gulab jamun', 'rasgulla']
                for exclude_item in diabetes_exclude:
                    filtered = filtered[~filtered['Ingredients'].str.lower().str.contains(exclude_item, na=False)]
                    filtered = filtered[~filtered['Name'].str.lower().str.contains(exclude_item, na=False)]
            
            elif condition_lower == "pcos":
                # Exclude dairy and gluten-heavy items
                pcos_exclude = ['dairy', 'milk', 'paneer', 'cheese', 'refined flour', 'wheat flour', 'cream']
                for exclude_item in pcos_exclude:
                    filtered = filtered[~filtered['Ingredients'].str.lower().str.contains(exclude_item, na=False)]
            
            elif condition_lower == "thyroid":
                # Exclude raw cruciferous vegetables and soy
                thyroid_exclude = ['raw broccoli', 'raw kale', 'raw cabbage', 'soy', 'tofu']
                for exclude_item in thyroid_exclude:
                    filtered = filtered[~filtered['Ingredients'].str.lower().str.contains(exclude_item, na=False)]
            
            elif condition_lower in ["hypertension", "high blood pressure"]:
                # Exclude high-sodium foods
                hypertension_exclude = ['pickle', 'papad', 'salt', 'processed', 'canned', 'achaar']
                for exclude_item in hypertension_exclude:
                    filtered = filtered[~filtered['Ingredients'].str.lower().str.contains(exclude_item, na=False)]
            
            elif condition_lower in ["kidney disease", "renal"]:
                # Exclude high-protein, high-potassium foods
                kidney_exclude = ['dal', 'rajma', 'chole', 'banana', 'potato', 'spinach']
                for exclude_item in kidney_exclude:
                    filtered = filtered[~filtered['Ingredients'].str.lower().str.contains(exclude_item, na=False)]
            
            elif condition_lower in ["heart disease", "cardiac"]:
                # Exclude high-fat, fried foods
                heart_exclude = ['fried', 'ghee', 'butter', 'cream', 'coconut oil', 'deep fried']
                for exclude_item in heart_exclude:
                    filtered = filtered[~filtered['Ingredients'].str.lower().str.contains(exclude_item, na=False)]
                    filtered = filtered[~filtered['Name'].str.lower().str.contains(exclude_item, na=False)]
    
    # 5. Filter by dislikes (COMPREHENSIVE)
    if dislikes:
        for dislike in dislikes:
            if dislike.strip():  # Skip empty strings
                dislike_lower = dislike.lower().strip()
                print(f"Filtering out dishes containing: {dislike_lower}")
                
                # Remove dishes containing disliked ingredients or dish names
                filtered = filtered[~filtered['Ingredients'].str.lower().str.contains(dislike_lower, na=False)]
                filtered = filtered[~filtered['Name'].str.lower().str.contains(dislike_lower, na=False)]
                
                # Handle common food categories
                if dislike_lower in ['spicy', 'hot']:
                    spicy_terms = ['chili', 'pepper', 'masala', 'spicy']
                    for term in spicy_terms:
                        filtered = filtered[~filtered['Ingredients'].str.lower().str.contains(term, na=False)]
                        filtered = filtered[~filtered['Name'].str.lower().str.contains(term, na=False)]
                
                elif dislike_lower in ['dairy', 'milk products']:
                    dairy_terms = ['milk', 'paneer', 'cheese', 'yogurt', 'dahi', 'cream', 'butter', 'ghee']
                    for term in dairy_terms:
                        filtered = filtered[~filtered['Ingredients'].str.lower().str.contains(term, na=False)]
                
                elif dislike_lower in ['nuts', 'dry fruits']:
                    nut_terms = ['almond', 'cashew', 'walnut', 'pistachio', 'nuts', 'badam']
                    for term in nut_terms:
                        filtered = filtered[~filtered['Ingredients'].str.lower().str.contains(term, na=False)]
    
    # 6. Filter by lab values (prioritize beneficial foods)
    if lab_values:
        for lab, status in lab_values.items():
            lab_lower = lab.lower()
            status_lower = status.lower()
            
            # Example: If high cholesterol, prefer dishes without high cholesterol ingredients
            if "cholesterol" in lab_lower and status_lower in ("high", "elevated"):
                cholesterol_avoid = ['egg yolk', 'red meat', 'organ meat', 'full fat dairy']
                for avoid_item in cholesterol_avoid:
                    filtered = filtered[~filtered['Ingredients'].str.lower().str.contains(avoid_item, na=False)]
    
    return filtered

def df_to_compact_dish_list(filtered_df):
    """
    Convert pre-filtered DataFrame to ultra-compact dish representation
    Only essential nutrition data - all filtering already done
    """
    dishes = []
    for _, row in filtered_df.iterrows():
        dishes.append({
            'name': row['Name'],
            'cal': int(row['Calories (kcal)']),
            'p': float(row['Protein (g)']),
            'c': float(row['Carbs (g)']),
            'f': float(row['Fat (g)']),
            'quantity' : row.get('Quantity (g)', '')
            # All filtering criteria already applied - no need for region/ingredients
        })
    return dishes

def create_dish_selection_from_csv(df, diet_type, region=None, health_conditions=None, dislikes=None, lab_values=None):
    """
    Create a curated list of dishes from the database with COMPREHENSIVE filtering
    Then convert to compact format for AI processing
    """
    if df is None:
        return None
    
    print(f"Starting with {len(df)} total dishes")
    print(f"Applying filters: diet_type={diet_type}, region={region}")
    print(f"Health conditions: {health_conditions}")
    print(f"Dislikes: {dislikes}")
    
    # Apply comprehensive filtering for each meal type
    breakfast_dishes = filter_dishes_by_preferences(df, diet_type, "breakfast", region, health_conditions, dislikes, lab_values)
    lunch_dishes = filter_dishes_by_preferences(df, diet_type, "lunch", region, health_conditions, dislikes, lab_values)
    dinner_dishes = filter_dishes_by_preferences(df, diet_type, "dinner", region, health_conditions, dislikes, lab_values)
    snack_dishes = filter_dishes_by_preferences(df, diet_type, "snack", region, health_conditions, dislikes, lab_values)
    
    print(f"After filtering - Breakfast: {len(breakfast_dishes)}, Lunch: {len(lunch_dishes)}, Dinner: {len(dinner_dishes)}, Snacks: {len(snack_dishes)}")
    
    # Optional: Limit dishes per meal type to control token usage
    MAX_DISHES_PER_MEAL = 30  # Adjust based on your token budget
    
    if len(breakfast_dishes) > MAX_DISHES_PER_MEAL:
        breakfast_dishes = breakfast_dishes.head(MAX_DISHES_PER_MEAL)
        print(f"Limited breakfast dishes to {MAX_DISHES_PER_MEAL}")
    
    if len(lunch_dishes) > MAX_DISHES_PER_MEAL:
        lunch_dishes = lunch_dishes.head(MAX_DISHES_PER_MEAL)
        print(f"Limited lunch dishes to {MAX_DISHES_PER_MEAL}")
    
    if len(dinner_dishes) > MAX_DISHES_PER_MEAL:
        dinner_dishes = dinner_dishes.head(MAX_DISHES_PER_MEAL)
        print(f"Limited dinner dishes to {MAX_DISHES_PER_MEAL}")
    
    if len(snack_dishes) > MAX_DISHES_PER_MEAL:
        snack_dishes = snack_dishes.head(MAX_DISHES_PER_MEAL)
        print(f"Limited snack dishes to {MAX_DISHES_PER_MEAL}")
    
    # Convert to compact dictionaries for AI processing (all filtering already done)
    dish_selection = {
        'breakfast': df_to_compact_dish_list(breakfast_dishes),
        'lunch': df_to_compact_dish_list(lunch_dishes),
        'dinner': df_to_compact_dish_list(dinner_dishes),
        'snack': df_to_compact_dish_list(snack_dishes)
    }
    
    # Validate we have enough dishes
    total_dishes = sum(len(dishes) for dishes in dish_selection.values())
    print(f"Final compact dish selection: {total_dishes} dishes total")
    
    if total_dishes < 10:
        print("WARNING: Very few dishes after filtering. Consider relaxing some constraints.")
    
    return dish_selection

def build_health_avoidance(conditions):
    avoid_rules = []
    for cond in conditions:
        lc = cond.lower()
        if lc == "diabetes":
            avoid_rules.append("- Diabetes: avoid refined sugars, sweets, white bread/rice, high-GI carbs.")
        elif lc == "pcos":
            avoid_rules.append("- PCOS: avoid dairy & gluten; use gluten-free or dairy-free swaps.")
        elif lc == "thyroid":
            avoid_rules.append("- Thyroid: avoid raw crucifers (broccoli, kale), soy, goitrogens; cooked OK.")
        elif lc == "hypertension":
            avoid_rules.append("- Hypertension: avoid high-sodium foods, pickles, processed foods.")
    return "\n".join(avoid_rules) if avoid_rules else "- None."

def build_ingredient_frequency(freq_cons):
    if freq_cons:
        return "\n".join(
            f"- Use {ing} ~{cnt}x/week, spaced out (not back-to-back)."
            for ing, cnt in freq_cons.items()
        )
    else:
        return "- None specified."

def build_dislikes_substitutions(dislikes):
    if dislikes:
        return "\n".join(
            f"- Exclude {item}; substitute with similar nutrient-dense alternatives."
            for item in dislikes
        )
    else:
        return "- None."

def build_lab_value_adjustments(lab_values):
    lab_lines = []
    for lab, status in lab_values.items():
        lab_l = lab.lower()
        stat_l = status.lower()
        if "b12" in lab_l and stat_l == "low":
            lab_lines.append("- Low B12: include eggs, dairy (if allowed), fish, or fortified yeast.")
        if "triglyceride" in lab_l and stat_l in ("high", "elevated"):
            lab_lines.append("- High triglycerides: fatty fish 2x/week, flax/chia seeds; avoid sweets.")
        if "cholesterol" in lab_l and stat_l in ("high", "elevated"):
            lab_lines.append("- High cholesterol: focus on soluble fiber and healthy fats; limit red meat.")
        if "iron" in lab_l and stat_l in ("low", "deficient"):
            lab_lines.append("- Iron deficiency: include spinach, legumes, tofu; pair with vitamin C sources.")
        if "vitamin d" in lab_l and stat_l in ("low", "deficient"):
            lab_lines.append("- Low Vit D: include fatty fish, egg yolks, mushrooms, fortified milk; advise sunlight.")
        if "blood pressure" in lab_l or "hypertension" in lab_l:
            lab_lines.append("- Hypertension: DASH diet—fruits, veggies, low-fat dairy; avoid added salt.")
    return "\n".join(lab_lines) if lab_lines else "- None."

def build_meal_distribution_and_diet_text(diet_type, meal_freq, non_veg):
    snack_ct = max(0, meal_freq - 3)
    dist_text = (
        f"Breakfast:20–25%, Lunch:30–35%, Dinner:30–35%, "
        f"Snacks:5–10% ({snack_ct} snack{'s' if snack_ct!=1 else ''}); redistribute if skipped."
    )
    dt = diet_type.lower()
    if dt == "non-vegetarian":
        diet_text = (
            f"limit to one animal-protein meal per day on {non_veg}. "
            "If suggesting a fish dish, also provide a chicken alternative separated by '/'."
        )
    elif dt == "eggetarian":
        diet_text = "Eggetarian: Only veg and eggs are allowed."
    elif dt == "jain":
        diet_text = "Jain: no eggs, root veg, honey, gelatin; use asafoetida."
    elif dt == "vegetarian":
        diet_text = "Vegetarian: no meat, fish, or eggs."
    else:
        diet_text = "Mixed: veg + non-veg allowed."
    return dist_text, diet_text

def build_region_text(region):
    rp = region.lower()
    if "north" in rp:
        return "North Indian: rotis, dals, sabzis, paneer, curd."
    elif "south" in rp:
        return "South Indian: rice/idli, dosa, upma, sambar."
    elif "western" in rp:
        return "Western: oatmeal, salads, grilled proteins."
    elif "eastern" in rp:
        return "Eastern: rice, fish, sweets, mustard oil."
    else:
        return "Mixed cuisine."

def clean_json_response(raw_text):
    """Clean and fix common JSON formatting issues"""
    # Strip markdown code fences
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        if len(lines) > 2:
            raw_text = "\n".join(lines[1:-1])
    
    # Remove comment lines
    clean_lines = []
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith(("//", "/*", "*/")):
            clean_lines.append(line)
    
    text = "\n".join(clean_lines)
    
    # Fix trailing commas - common GPT issue
    import re
    # Remove trailing commas before closing brackets/braces
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    
    # Remove trailing commas before newlines followed by closing brackets
    text = re.sub(r',(\s*\n\s*[}\]])', r'\1', text)
    
    return text

def validate_calorie_targets(plan, target_calories):
    """Validate that each day meets the calorie target"""
    days = plan.get("7DayPlan", [])
    validation_results = []
    
    for day_entry in days:
        day_name = day_entry.get("Day", "Unknown")
        day_total = 0
        
        for meal_name, meal_data in day_entry.items():
            if meal_name != "Day" and isinstance(meal_data, dict):
                for dish_key, dish_info in meal_data.items():
                    if isinstance(dish_info, dict):
                        day_total += float(dish_info.get('calories', 0))
        
        validation_results.append({
            'day': day_name,
            'total': day_total,
            'target': target_calories,
            'difference': day_total - target_calories,
            'within_range': abs(day_total - target_calories) <= 150  # Allow 100 kcal tolerance
        })
    
    return validation_results

def convert_non_veg_days(avoid_non_veg_days):
    """
    Convert days when user avoids non-veg to days when user prefers non-veg
    """
    all_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    if not avoid_non_veg_days:
        return all_days  # If no restrictions, allow all days
    
    # Convert to lowercase for comparison
    avoid_days_lower = [day.lower() for day in avoid_non_veg_days if day.strip()]
    
    # Find days when non-veg IS preferred (opposite of avoid days)
    non_veg_days = []
    for day in all_days:
        if day.lower() not in avoid_days_lower:
            non_veg_days.append(day)
    
    return non_veg_days

def assemble_compact_prompt(payload, dish_selection, target_calories):
    """
    Create ultra-compact prompt to minimize token usage
    Adapts to meal frequency (3, 4, 5 meals/day)
    """

    profile = payload.get("user_profile", {})
    diet_type = profile.get("Diet type", "Mixed")
    meal_freq = int(profile.get("Meal frequency in a day", 3))


    # Decide meal structure
    meals = ["Breakfast", "Lunch", "Dinner"]
    snack_count = 0

    if meal_freq == 4:
        meals.insert(2, "Snack")
        snack_count = 1
    elif meal_freq == 5:
        meals.insert(2, "Snack1")
        meals.insert(4, "Snack2")
        snack_count = 2

    # Correct calorie distribution
    if meal_freq == 3:
        b_target = int(target_calories * 0.25)
        l_target = int(target_calories * 0.35)
        d_target = int(target_calories * 0.40)
        s_targets = []
    elif meal_freq == 4:
        b_target = int(target_calories * 0.22)
        l_target = int(target_calories * 0.33)
        d_target = int(target_calories * 0.33)
        s_targets = [int(target_calories * 0.12)]
    elif meal_freq == 5:
        b_target = int(target_calories * 0.20)
        l_target = int(target_calories * 0.30)
        d_target = int(target_calories * 0.30)
        s_targets = [int(target_calories * 0.10), int(target_calories * 0.10)]
    else:
        raise ValueError(f"Unsupported meal frequency: {meal_freq}")

    print(f"Meal structure: {meals}")
    print(f"Calories => B:{b_target}, L:{l_target}, D:{d_target}" + (
        f", S:{s_targets}" if s_targets else ""))

    # Compose meal blocks
    meal_dish_blocks = []
    for meal in meals:
        meal_key = meal.lower().replace("1", "").replace("2", "")  # normalize snack1/snack2
        dishes = dish_selection.get(meal_key, [])
        block = f"{meal.upper()} ({len(dishes)} options):\n" + json.dumps(dishes, separators=(',', ':'))
        meal_dish_blocks.append(block)

    meal_blocks = "\n\n".join(meal_dish_blocks)

    # Generate JSON structure for GPT response
    meal_json_fields = []
    for meal in meals:
        meal_json_fields.append(f'"{meal}":{{"Dish1":{{"name":"...","quantity":"...","calories":X,"protein":X,"carbs":X,"fats":X}}}}')

    daily_json = "{\n" + '"Day":"Day 1",\n' + ",\n".join(meal_json_fields) + "\n}"

    # Generate target block for prompt
    target_block = f"- Breakfast: {b_target} kcal\n- Lunch: {l_target} kcal\n"
    if snack_count == 1:
        target_block += f"- Snack: {s_targets[0]} kcal\n"
    elif snack_count == 2:
        target_block += f"- Snack1: {s_targets[0]} kcal\n- Snack2: {s_targets[1]} kcal\n"
    target_block += f"- Dinner: {d_target} kcal"

    prompt = f"""Create a 7-day diet plan. Each day MUST total exactly {target_calories} kcal.

AVAILABLE DISHES (name,cal,p,c,f,quantity):

{meal_blocks}

TARGET CALORIES PER MEAL:
{target_block}

RULES:
- Combine 2‒4 dishes per meal if needed to reach the calorie target.
- You can scale any dish up or down (e.g., 1.5x or 2x quantity).
- Always update the "quantity" field to reflect the new portion (e.g., "350 g", "2 rotis").
- Use the exact nutrition values provided and scale them accurately.
- You must hit the calorie target for each meal as closely as possible.
- It's okay to repeat compatible dishes in the same meal if necessary.
- **A dish may appear max 2 times in the entire week and never on two consecutive days.**
- **Do NOT include a dish if the scaled amount would be < 25 g / 25 ml / ½ roti / ½ piece.**
- Return valid JSON (no extra text).


JSON FORMAT:
{{
  "7DayPlan": [
    {daily_json},
    {{... Day 2 ...}},
    ...
    {{... Day 7 ...}}
  ],
  "Summary": {{
    "AverageCalories": "{target_calories} kcal/day",
    "AverageMacros": {{ "Protein": "XXg", "Carbs": "XXg", "Fats": "XXg" }}
  }}
}}

Each day must total exactly {target_calories} kcal.
"""
    return prompt


def assemble_prompt(payload, dist_text, freq_text, sub_text, skip_text, safe_text, variety_text, avoid_text, lab_text, hydration_text, diet_text, region_text, dish_selection=None):
    profile = payload.get("user_profile", {})
    calorie_goal = payload.get("calorie_goal", "1500 kcal/day")
    target_calories = int(calorie_goal.split()[0])
    meal_freq = int(profile.get("Meal frequency in a day", 3))


    diet_type = profile.get("Diet type", "Mixed")

    # Decide meal structure
    meals = ["Breakfast", "Lunch", "Dinner"]
    snack_count = 0

    if meal_freq == 4:
        meals.insert(2, "Snack")
        snack_count = 1
    elif meal_freq == 5:
        meals.insert(2, "Snack1")
        meals.insert(4, "Snack2")
        snack_count = 2

    # Correct calorie distribution
    if meal_freq == 3:
        b_target = int(target_calories * 0.25)
        l_target = int(target_calories * 0.35)
        d_target = int(target_calories * 0.40)
        s_targets = []
    elif meal_freq == 4:
        b_target = int(target_calories * 0.22)
        l_target = int(target_calories * 0.33)
        d_target = int(target_calories * 0.33)
        s_targets = [int(target_calories * 0.12)]
    elif meal_freq == 5:
        b_target = int(target_calories * 0.20)
        l_target = int(target_calories * 0.30)
        d_target = int(target_calories * 0.30)
        s_targets = [int(target_calories * 0.10), int(target_calories * 0.10)]
    else:
        raise ValueError("Unsupported meal frequency.")

    # If we have dish selection from CSV, use compact prompt
    if dish_selection:
        return assemble_compact_prompt(payload, dish_selection, target_calories)

    # Fallback to full prompt
    meal_targets_text = f"- Breakfast: {b_target} kcal\n- Lunch: {l_target} kcal\n"
    if snack_count == 1:
        meal_targets_text += f"- Snack: {s_targets[0]} kcal\n"
    elif snack_count == 2:
        meal_targets_text += f"- Snack1: {s_targets[0]} kcal\n- Snack2: {s_targets[1]} kcal\n"
    meal_targets_text += f"- Dinner: {d_target} kcal"

    payload_str = json.dumps(payload, indent=2)

    prompt = f"""
Create a 7-day diet plan with EXACT calorie targets. Each day must total {target_calories} kcal.

User Details: {payload_str}

MEAL CALORIE TARGETS (MANDATORY):
{meal_targets_text}

REQUIREMENTS:
1. Include multiple dishes per meal to reach exact calorie targets
2. Use realistic portions and add complementary foods (milk, fruits, nuts, etc.)
3. If needed, modify the quantity of the dish to reach the calorie/macros target and must include it.
4. Diet type: {diet_type}
5. Regional preference: {region_text}

Return ONLY this JSON structure (no extra text, no trailing commas):

{{
  "7DayPlan": [
    {{
      "Day": "Day 1",
      "Breakfast": {{
        "Dish1": {{"name": "Dish A", "quantity": "1 bowl", "calories": 250, "protein": 10, "carbs": 35, "fats": 8}},
        "Dish2": {{"name": "Dish B", "quantity": "1 cup", "calories": 150, "protein": 5, "carbs": 20, "fats": 4}}
      }},
      "Lunch": {{
        "Dish1": {{"name": "Dish C", "quantity": "1 plate", "calories": 500, "protein": 20, "carbs": 60, "fats": 12}}
      }},
""" + (
        f"""      "Snack": {{
        "Dish1": {{"name": "Dish S", "quantity": "1 bowl", "calories": {s_targets[0]}, "protein": 6, "carbs": 25, "fats": 5}}
      }},
""" if snack_count == 1 else
        f"""      "Snack1": {{
        "Dish1": {{"name": "Dish S1", "quantity": "1 bowl", "calories": {s_targets[0]}, "protein": 6, "carbs": 25, "fats": 5}}
      }},
      "Snack2": {{
        "Dish1": {{"name": "Dish S2", "quantity": "1 bowl", "calories": {s_targets[1]}, "protein": 6, "carbs": 25, "fats": 5}}
      }},
""" if snack_count == 2 else ""
    ) + f"""      "Dinner": {{
        "Dish1": {{"name": "Dish D", "quantity": "1 plate", "calories": {d_target}, "protein": 18, "carbs": 40, "fats": 12}}
      }}
    }},
    {{... Day 2 ...}},
    ...
    {{... Day 7 ...}}
  ],
  "Summary": {{
    "AverageCalories": "{target_calories} kcal/day",
    "AverageMacros": {{ "Protein": "XXg", "Carbs": "XXg", "Fats": "XXg" }}
  }}
}}

Each day must total exactly {target_calories} kcal.
"""
    return prompt

def call_openai_with_retry(prompt, model, target_calories=1667, max_retries=5):
    """
    Enhanced retry with exponential backoff for rate limits and better error handling
    """
    last_clean = None
    
    for attempt in range(1, max_retries + 1):
        try:
            resp = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role":"system","content":"You are a precision dietitian. Use only the given dishes. You MUST reach exact calorie targets by combining and scaling dishes as needed. Do NOT underdeliver on calories."
},
                    {"role":"user","content":prompt}
                ],
                temperature=0.3,
                max_tokens= 8000
            )
            raw = resp.choices[0].message.content.strip()
            
        except openai.error.RateLimitError as e:
            wait_time = (2 ** attempt) + random.uniform(0, 1)  # Exponential backoff
            print(f"Attempt {attempt}: Rate limit hit. Waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
            continue
            
        except Exception as e:
            print(f"Attempt {attempt}: API call failed: {e}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)  # Wait before retry
                continue
            else:
                break
        
        # Clean the JSON response
        clean = clean_json_response(raw)
        last_clean = clean
        
        try:
            plan = json.loads(clean)
        except JSONDecodeError as e:
            print(f"Attempt {attempt}: JSON decode error: {e}")
            continue
            
        days = plan.get("7DayPlan")
        if isinstance(days, list) and len(days) == 7:
            # Validate calorie targets
            validation = validate_calorie_targets(plan, target_calories)
            days_within_range = sum(1 for v in validation if v['within_range'])
            
            print(f"\nAttempt {attempt} - Calorie Validation:")
            for v in validation:
                status = "OK" if v['within_range'] else "X"
                print(f"  {status} {v['day']}: {v['total']:.0f} kcal (target: {v['target']}, diff: {v['difference']:+.0f})")
            
            if days_within_range >= 4:  # At least 5 out of 7 days should be close
                print(f"OK Acceptable plan: {days_within_range}/7 days within target range")
                return plan
            else:
                print(f"X Plan rejected: Only {days_within_range}/7 days within target range")
                continue
        else:
            print(f"Attempt {attempt}: Invalid structure - got {len(days) if isinstance(days, list) else 'non-list'} days")
                
    raise ValueError(f"Failed to get properly calibrated 7-day plan after {max_retries} attempts. Last response:\n{last_clean}")

def get_diet_plan_via_gpt(payload: dict, model: str = "gpt-4o", csv_path: str = "samples/CuisineList.csv") -> dict:
    """
    Main function to generate diet plan via GPT with optimized filtering and token usage
    """
    profile = payload.get("user_profile", {})
    diet_type = profile.get("Diet type", "Mixed")
    meal_freq = int(profile.get("Meal frequency in a day", 3))
    
    # Convert "days to avoid non-veg" to "days to prefer non-veg"
    avoid_non_veg_days = profile.get("Non-Veg Days", [])
    non_veg_days = convert_non_veg_days(avoid_non_veg_days)
    print(f"Non-veg avoid days: {avoid_non_veg_days}")
    print(f"Non-veg preferred days: {non_veg_days}")
    
    conditions = profile.get("Health Conditions", [])
    region = profile.get("Culture preference", "Mixed")
    freq_cons = profile.get("Ingredient Frequency", {})
    dislikes = profile.get("Dislikes", [])
    lab_values = profile.get("Lab Values", {})
    
    # Extract target calories
    calorie_goal = payload.get("calorie_goal", "1500 kcal/day")
    target_calories = int(calorie_goal.split()[0])

    # Load cuisine database
    cuisine_df = load_cuisine_database(csv_path)
    dish_selection = None
    
    if cuisine_df is not None:
        # Create dish selection from CSV with all filtering parameters
        dish_selection = create_dish_selection_from_csv(
            cuisine_df, 
            diet_type, 
            region=region, 
            health_conditions=conditions, 
            dislikes=dislikes, 
            lab_values=lab_values
        )

        debug_dish_distribution(dish_selection)
        
        # Check if we have enough dishes after filtering
        if dish_selection:
            total_dishes = sum(len(dishes) for dishes in dish_selection.values())
            print(f"After filtering: {total_dishes} dishes available")
            
            if total_dishes < 10:  # Need at least 10 dishes for variety
                print("Warning: Limited dish variety after filtering. Consider expanding the database or relaxing constraints.")
                
            # Check individual meal types, allow skipping snack if meal_freq is 3
            meal_freq = int(profile.get("Meal frequency in a day", 3))

            for meal_type, dishes in dish_selection.items():
                if meal_type == "snack" and meal_freq == 3:
                    continue  # ✅ skip snack validation for 3-meal plans
                if len(dishes) == 0:
                    print(f"ERROR: No {meal_type} dishes available after filtering!")
                    return None

        else:
            print("No dishes found matching all the preferences.")
            return None
    
    # Build constraint texts (keeping original functionality for fallback)
    avoid_text = build_health_avoidance(conditions)
    freq_text = build_ingredient_frequency(freq_cons)
    sub_text = build_dislikes_substitutions(dislikes)
    skip_text = (
        "If meal frequency <3, omit Breakfast and redistribute its calories. "
        "If user skips Dinner, redistribute dinner calories to other meals/snacks."
    )
    safe_text = (
        "If activity level or metrics are missing, assume lightly active (x1.375) "
        "and note 'assuming lightly active lifestyle.'"
    )
    variety_text = (
        "No dish repeat within Week 1. Weeks 2–4 repeat Week 1's menu unless user requests more variety."
    )
    lab_text = build_lab_value_adjustments(lab_values)
    hydration_text = "- Remind to drink 2–3 L water/day; include sleep/activity tip if relevant."
    dist_text, diet_text = build_meal_distribution_and_diet_text(diet_type, meal_freq, non_veg_days)
    region_text = build_region_text(region)

    # Create prompt with or without CSV dishes
    prompt = assemble_prompt(
        payload, dist_text, freq_text, sub_text, skip_text, safe_text, variety_text,
        avoid_text, lab_text, hydration_text, diet_text, region_text, dish_selection
    )
    
    return call_openai_with_retry(prompt, model, target_calories)

def debug_dish_distribution(dish_selection):
    """Enhanced debug function to show filtering results"""
    print("\n=== FILTERED Meal Distribution Debug ===")
    for meal_type, dishes in dish_selection.items():
        print(f"{meal_type}: {len(dishes)} dishes")
        if dishes:
            print("  Sample dishes:")
            for i, dish in enumerate(dishes[:3]):  # Show first 3
                print(f"    {i+1}. {dish['name']} ({dish['cal']} cal)")
        else:
            print("  WARNING: No dishes available!")
    print("=========================================\n")

# Additional utility functions for enhanced functionality

def estimate_token_usage(dish_selection):
    if not dish_selection:
        return 0
    total_dishes = sum(len(d) for d in dish_selection.values())
    return total_dishes * 20 + 1000  # add buffer for base prompt


def optimize_dish_selection_for_tokens(dish_selection, max_tokens=8000):
    """
    Dynamically adjust dish limits based on token budget
    """
    estimated_tokens = estimate_token_usage(dish_selection)
    
    if estimated_tokens <= max_tokens:
        return dish_selection
    
    print(f"Estimated tokens ({estimated_tokens}) exceed limit ({max_tokens}). Optimizing...")
    
    # Calculate how many dishes we can afford
    available_tokens = max_tokens - 700  # Reserve tokens for base prompt
    tokens_per_dish = 18
    max_total_dishes = available_tokens // tokens_per_dish
    
    # Distribute dishes proportionally
    total_current_dishes = sum(len(dishes) for dishes in dish_selection.values())
    scaling_factor = max_total_dishes / total_current_dishes
    
    optimized_selection = {}
    for meal_type, dishes in dish_selection.items():
        max_for_meal = max(3, int(len(dishes) * scaling_factor))  # Minimum 3 per meal
        optimized_selection[meal_type] = dishes[:max_for_meal]
        
    print(f"Optimized from {total_current_dishes} to {sum(len(dishes) for dishes in optimized_selection.values())} dishes")
    
    return optimized_selection

def validate_dish_selection(dish_selection):
    """
    Validate that we have sufficient dishes for meal planning
    """
    issues = []
    
    for meal_type, dishes in dish_selection.items():
        if len(dishes) == 0:
            issues.append(f"No {meal_type} dishes available")
        elif len(dishes) < 3:
            issues.append(f"Very few {meal_type} dishes ({len(dishes)}) - may limit variety")
    
    total_dishes = sum(len(dishes) for dishes in dish_selection.values())
    if total_dishes < 15:
        issues.append(f"Total dishes ({total_dishes}) very low - consider relaxing filters")
    
    if issues:
        print("VALIDATION WARNINGS:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    
    return True

# Enhanced main function with better error handling
def get_diet_plan_via_gpt_enhanced(payload: dict, model: str = "gpt-4o", csv_path: str = "samples/CuisineList.csv", max_tokens: int = 8000) -> dict:
    """
    Enhanced version with better error handling and optimization
    """
    try:
        # Get basic plan first
        plan = get_diet_plan_via_gpt(payload, model, csv_path)
        
        if plan is None:
            print("Failed to generate plan with current filters. Trying with relaxed constraints...")
            
            # Try with relaxed dislikes
            profile = payload.get("user_profile", {})
            original_dislikes = profile.get("Dislikes", [])
            
            if len(original_dislikes) > 2:
                profile["Dislikes"] = original_dislikes[:2]  # Keep only top 2 dislikes
                print(f"Relaxed dislikes to: {profile['Dislikes']}")
                plan = get_diet_plan_via_gpt(payload, model, csv_path)
            
            if plan is None and len(original_dislikes) > 0:
                profile["Dislikes"] = []  # Remove all dislikes
                print("Removed all dislikes")
                plan = get_diet_plan_via_gpt(payload, model, csv_path)
        
        return plan
        
    except Exception as e:
        print(f"Error in enhanced diet plan generation: {e}")
        return None