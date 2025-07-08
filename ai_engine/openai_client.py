import os
import json
import openai
import pandas as pd
import random
from dotenv import load_dotenv
from json import JSONDecodeError

# ─── 1. Load your API key ────────────────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in your .env file")
openai.api_key = API_KEY

# ─── 2. LOAD CUISINE DATABASE FROM CSV ──────────────────────────────────────
import pandas as pd

def load_cuisine_database(csv_file_path="samples/CuisineList.csv"):
    """Load cuisine database from CSV file"""
    try:
        # Using pandas for better CSV handling
        df = pd.read_csv(csv_file_path)
        
        # Clean column names (remove extra spaces and standardize)
        df.columns = df.columns.str.strip()
        
        print(f"📋 Columns found: {list(df.columns)}")
        
        # Create column mapping for common variations
        column_mapping = {}
        for col in df.columns:
            col_clean = col.strip().lower()
            if 'name' in col_clean and 'employee' not in col_clean:
                column_mapping['Name'] = col
            elif 'state' in col_clean or 'region' in col_clean:
                column_mapping['State/Region'] = col
            elif 'quantity' in col_clean or 'qty' in col_clean:
                column_mapping['Quantity'] = col
            elif 'calories' in col_clean:
                column_mapping['Calories (kcal)'] = col
            elif 'protein' in col_clean:
                column_mapping['Protein (g)'] = col
            elif 'carb' in col_clean:
                column_mapping['Carbs (g)'] = col
            elif 'fat' in col_clean:
                column_mapping['Fat (g)'] = col
            elif 'veg' in col_clean or 'vegetarian' in col_clean:
                column_mapping['Veg/Non-Veg'] = col
            elif 'meal' in col_clean and 'type' in col_clean:
                column_mapping['Meal Type'] = col
            elif 'ingredient' in col_clean:
                column_mapping['Ingredients'] = col
        
        print(f"🔄 Column mapping: {column_mapping}")
        
        cuisine_database = []
        for _, row in df.iterrows():
            try:
                dish = {
                    "name": str(row[column_mapping.get('Name', 'Name')]).strip(),
                    "region": str(row[column_mapping.get('State/Region', 'State/Region')]).strip(),
                    "quantity": str(row[column_mapping.get('Quantity', 'Quantity')]).strip(),
                    "calories": int(float(row[column_mapping.get('Calories (kcal)', 'Calories (kcal)')])),
                    "protein": int(float(row[column_mapping.get('Protein (g)', 'Protein (g)')])),
                    "carbs": int(float(row[column_mapping.get('Carbs (g)', 'Carbs (g)')])),
                    "fat": int(float(row[column_mapping.get('Fat (g)', 'Fat (g)')])),
                    "veg_type": str(row[column_mapping.get('Veg/Non-Veg', 'Veg/Non-Veg')]).strip(),
                    "meal_type": str(row[column_mapping.get('Meal Type', 'Meal Type')]).strip(),
                    "ingredients": str(row[column_mapping.get('Ingredients', 'Ingredients')]).strip()
                }
                cuisine_database.append(dish)
            except Exception as e:
                print(f"⚠️  Skipping row due to error: {e}")
                continue
        
        print(f"✅ Loaded {len(cuisine_database)} dishes from {csv_file_path}")
        return cuisine_database
        
    except FileNotFoundError:
        print(f"❌ CSV file '{csv_file_path}' not found. Using fallback dishes.")
        return get_fallback_dishes()
    except Exception as e:
        print(f"❌ Error loading CSV: {e}. Using fallback dishes.")
        return get_fallback_dishes()

def get_fallback_dishes():
    """Fallback dishes if CSV loading fails"""
    return [
        {
            "name": "Dal Tadka + Brown Rice + Mixed Vegetable Sabzi",
            "region": "North India",
            "quantity": "1 medium bowl dal (150g) + 1 cup rice (150g) + 1 small bowl sabzi (100g)",
            "calories": 450,
            "protein": 18,
            "carbs": 75,
            "fat": 8,
            "veg_type": "Vegetarian",
            "meal_type": "Lunch/Dinner",
            "ingredients": "Toor dal, brown rice, seasonal vegetables, turmeric, cumin, mustard seeds, ginger, tomato"
        }
        # Add a few more fallback dishes if needed
    ]

# Load the database once when module is imported
CUISINE_DATABASE = load_cuisine_database("samples/CuisineList.csv")

def filter_cuisine_by_preferences(user_profile):
    """Filter cuisine database based on user preferences - SMART FILTERING"""
    diet_type = user_profile.get("Diet type", "Mixed").lower()
    culture_pref = user_profile.get("Culture preference", "Mixed").lower()
    
    print(f"🔍 Filtering dishes for: Diet={diet_type}, Culture={culture_pref}")
    
    filtered_dishes = []
    
    for dish in CUISINE_DATABASE:
        # 1. Diet filtering
        if diet_type == "vegetarian" and dish["veg_type"] != "Vegetarian":
            continue
        elif diet_type == "eggetarian" and dish["veg_type"] not in ["Vegetarian", "Eggetarian"]:
            continue
        
        # 2. Region filtering (if not "both" or "mixed")
        if culture_pref in ["north", "northern"] and "North India" not in dish["region"]:
            continue
        elif culture_pref in ["south", "southern"] and "South India" not in dish["region"]:
            continue
        elif culture_pref in ["west", "western"] and "Western India" not in dish["region"]:
            continue
        elif culture_pref in ["east", "eastern"] and "Eastern India" not in dish["region"]:
            continue
        elif "only indian" in culture_pref:
            # For "Only Indian" preference, include all Indian regional dishes
            pass  # Include all Indian dishes
        
        filtered_dishes.append(dish)
    
    # Force limit to 100 dishes max (reduced from 150 to save tokens)
    if len(filtered_dishes) > 100:
        import random
        filtered_dishes = random.sample(filtered_dishes, 100)
        print(f"📊 Sampled 100 dishes from {len(CUISINE_DATABASE)} total")
    else:
        print(f"📊 Filtered to {len(filtered_dishes)} dishes")
    
    return filtered_dishes

def parse_quantity(quantity):
    """Parse quantity string like '2 pieces (100g)' into ('2 pieces', '100g')"""
    if '(' in quantity and ')' in quantity:
        main, weight = quantity.split('(', 1)
        main = main.strip()
        weight = weight.strip(') ').strip()
        return main, weight
    else:
        return quantity.strip(), ''

def format_cuisine_for_prompt(filtered_dishes):
    """Format the filtered dishes for GPT prompt - OPTIMIZED FOR TOKENS"""
    if not filtered_dishes:
        return "No suitable dishes found in database. Please use general healthy options."
    
    # Group by meal type
    breakfast_dishes = [d for d in filtered_dishes if "Breakfast" in d["meal_type"]]
    lunch_dinner_dishes = [d for d in filtered_dishes if "Lunch" in d["meal_type"] or "Dinner" in d["meal_type"]]
    
    formatted = "**DATABASE DISHES (USE ONLY THESE):**\n"
    
    if breakfast_dishes:
        formatted += "**BREAKFAST:**\n"
        for dish in breakfast_dishes[:20]:  # Limit to 20 breakfast dishes
            qty, weight = parse_quantity(dish['quantity'])
            if weight:
                formatted += f"- {dish['name']} ({qty}, {weight})\n"
            else:
                formatted += f"- {dish['name']} ({qty})\n"
        formatted += "\n"
    
    if lunch_dinner_dishes:
        formatted += "**LUNCH/DINNER:**\n"
        for dish in lunch_dinner_dishes[:60]:  # Limit to 60 lunch/dinner dishes
            qty, weight = parse_quantity(dish['quantity'])
            if weight:
                formatted += f"- {dish['name']} ({qty}, {weight})\n"
            else:
                formatted += f"- {dish['name']} ({qty})\n"
        formatted += "\n"
    
    formatted += "**RULES:** Use ONLY listed dishes with EXACT quantities shown. No repeats >2x/week. Different dishes each day."
    
    return formatted

def build_health_avoidance(conditions):
    avoid_rules = []
    for cond in conditions:
        lc = cond.lower()
        if lc == "diabetes":
            avoid_rules.append("- Diabetes: Choose dishes with carbs <70g per meal from the database.")
        elif lc == "pcos":
            avoid_rules.append("- PCOS: Prefer dishes with lower carbs and higher protein from database.")
        elif lc == "thyroid":
            avoid_rules.append("- Thyroid: Choose dishes without excessive soy from database.")
    return "\n".join(avoid_rules) if avoid_rules else "- None."

def build_ingredient_frequency(freq_cons):
    if freq_cons:
        return "\n".join(
            f"- Use dishes containing {ing} ~{cnt}x/week from database, spaced out."
            for ing, cnt in freq_cons.items()
        )
    else:
        return "- None specified."

def build_dislikes_substitutions(dislikes):
    if dislikes:
        return "\n".join(
            f"- Exclude dishes containing {item} from database selection."
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
            lab_lines.append("- Low B12: prefer dishes with eggs, dairy, fish from database.")
        if "triglyceride" in lab_l and stat_l in ("high", "elevated"):
            lab_lines.append("- High triglycerides: choose fish dishes from database, avoid high-fat options.")
        if "cholesterol" in lab_l and stat_l in ("high", "elevated"):
            lab_lines.append("- High cholesterol: prefer vegetarian dishes with high fiber from database.")
        if "iron" in lab_l and stat_l in ("low", "deficient"):
            lab_lines.append("- Iron deficiency: choose dishes with spinach, legumes from database.")
        if "vitamin d" in lab_l and stat_l in ("low", "deficient"):
            lab_lines.append("- Low Vit D: prefer fish or egg dishes from database.")
        if "blood pressure" in lab_l or "hypertension" in lab_l:
            lab_lines.append("- Hypertension: choose low-sodium dishes from database.")
    return "\n".join(lab_lines) if lab_lines else "- None."

def build_meal_distribution_and_diet_text(diet_type, meal_freq, non_veg):
    snack_ct = max(0, meal_freq - 3)
    dist_text = (
        f"Breakfast:20-25%, Lunch:30-35%, Dinner:30-35%, "
        f"Snacks:5-10% ({snack_ct} snack{'s' if snack_ct!=1 else ''}); redistribute if skipped."
    )
    dt = diet_type.lower()
    if dt == "non-vegetarian":
        diet_text = (
            f"Non-Veg: select from non-veg dishes in database for max one meal per day on {non_veg}. "
            "For other meals, use vegetarian dishes from database."
        )
    elif dt == "eggetarian":
        diet_text = "Eggetarian: select from vegetarian and egg dishes in database only."
    elif dt == "jain":
        diet_text = "Jain: select only vegetarian dishes from database (no root vegetables)."
    elif dt == "vegetarian":
        diet_text = "Vegetarian: select only vegetarian dishes from database."
    else:
        diet_text = "Mixed: select from all available dishes in database."
    return dist_text, diet_text

def build_region_text(region):
    rp = region.lower()
    if "north" in rp:
        return "North Indian: Select North Indian dishes from database."
    elif "south" in rp:
        return "South Indian: Select South Indian dishes from database."
    elif "western" in rp:
        return "Western: Select Western Indian dishes from database."
    else:
        return "Mixed cuisine: Select from all regional dishes in database."

def assemble_prompt(payload, dist_text, freq_text, sub_text, skip_text, safe_text, variety_text, avoid_text, lab_text, hydration_text, diet_text, region_text, cuisine_database_text):
    # Create a concise payload summary instead of full JSON
    profile = payload.get("user_profile", {})
    payload_summary = f"User: {profile.get('Name of the employee', 'Unknown')}, Age: {profile.get('Age', 'N/A')}, Weight: {profile.get('Weight & Height', 'N/A')}, Goals: {profile.get('Goals', 'N/A')}"
    
    prompt = f"""You are a certified dietitian. Create a 7-day diet plan using ONLY dishes from the provided database.

**USER PROFILE:** {payload_summary}

{cuisine_database_text}

**CONSTRAINTS:**
- Meal Distribution: {dist_text}
- Diet: {diet_text}
- Region: {region_text}
- Health: {avoid_text}
- Lab Values: {lab_text}
- Dislikes: {sub_text}
- Frequency: {freq_text}

**CRITICAL:** When listing dishes in the plan, use ONLY the user-friendly quantity format from the database. For example, if database shows "Gobi Paratha + Dahi + Achaar | Qty: 240g (2 parathas + 1 small bowl + 1 tbsp)", then in the plan write "2 Gobi Paratha + 1 small bowl Dahi + 1 tbsp achaar". Do NOT include calories or macros in the meal plan - only the dish name with quantities.

**RULES:** Use ONLY listed dishes with EXACT quantities. No repeats >2x/week. Different dishes each day.

Return ONLY valid JSON with exactly 7 days:
{{
  "7DayPlan": [ /* 7 day-objects */ ],
  "Summary": {{ "AverageCalories": "### kcal/day", "AverageMacros": {{ "Protein":"##g","Carbs":"##g","Fats":"##g" }} }}
}}"""
    return prompt

def call_openai_with_retry(prompt, model):
    last_clean = None
    for attempt in range(1, 4):
        resp = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role":"system","content":"You return only valid JSON diet plans using ONLY dishes from the provided database."},
                {"role":"user","content":prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        raw = resp.choices[0].message.content.strip()
        # strip fences
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(lines[1:-1])
        # remove comment lines
        clean_lines = [l for l in raw.splitlines() if not l.strip().startswith(("//","/*","*/"))]
        clean = "\n".join(clean_lines)
        last_clean = clean
        try:
            plan = json.loads(clean)
        except JSONDecodeError:
            continue
        days = plan.get("7DayPlan")
        if isinstance(days, list) and len(days) == 7:
            return plan
    raise ValueError(f"Failed to get exactly 7 days after 3 attempts. Last response:\n{last_clean}")

def calculate_quantity_multiplier(goal: str, user_profile: dict) -> float:
    """Calculate quantity multiplier based on user's goal and profile"""
    goal_lower = goal.lower()
    
    # Base multipliers for different goals
    if "fat loss" in goal_lower or "weight loss" in goal_lower:
        base_multiplier = 0.8  # Reduce portions for fat loss
    elif "muscle gain" in goal_lower or "muscle building" in goal_lower:
        base_multiplier = 1.2  # Increase portions for muscle gain
    elif "weight gain" in goal_lower:
        base_multiplier = 1.3  # Increase portions for weight gain
    else:
        base_multiplier = 1.0  # Maintain portions for general wellness
    
    # Adjust based on activity level
    activity = user_profile.get("Activity level", "Moderately active").lower()
    if "very active" in activity or "highly active" in activity:
        activity_multiplier = 1.1
    elif "sedentary" in activity or "low" in activity:
        activity_multiplier = 0.9
    else:
        activity_multiplier = 1.0
    
    # Adjust based on meal frequency
    meal_freq = int(user_profile.get("Meal frequency in a day", 3))
    if meal_freq > 3:
        frequency_multiplier = 0.9  # Smaller portions if more meals
    elif meal_freq < 3:
        frequency_multiplier = 1.1  # Larger portions if fewer meals
    else:
        frequency_multiplier = 1.0
    
    final_multiplier = base_multiplier * activity_multiplier * frequency_multiplier
    
    # Ensure multiplier stays within reasonable bounds
    return max(0.6, min(1.5, final_multiplier))

def adjust_quantity_with_multiplier(quantity_str: str, multiplier: float) -> str:
    """Adjust quantity string based on multiplier"""
    if not quantity_str or multiplier == 1.0:
        return quantity_str
    
    # Simple quantity adjustment - this can be enhanced
    if "bowl" in quantity_str.lower():
        return f"{multiplier:.1f} bowl"
    elif "cup" in quantity_str.lower():
        return f"{multiplier:.1f} cup"
    elif "piece" in quantity_str.lower():
        return f"{multiplier:.1f} pieces"
    else:
        return quantity_str

def get_diet_plan_via_gpt(payload: dict, model: str = "gpt-4", csv_path: str = "samples/CuisineList.csv") -> dict:
    profile     = payload.get("user_profile", {})
    diet_type   = profile.get("Diet type", "Mixed")
    meal_freq   = int(profile.get("Meal frequency in a day", 3))
    non_veg     = profile.get("Non-Veg Days", [])
    conditions  = profile.get("Health Conditions", [])
    region      = profile.get("Culture preference", "Mixed")
    freq_cons   = profile.get("Ingredient Frequency", {})
    dislikes    = profile.get("Dislikes", [])
    lab_values  = profile.get("Lab Values", {})

    # Load fresh database if different CSV path provided
    global CUISINE_DATABASE
    if csv_path != "samples/CuisineList.csv":
        CUISINE_DATABASE = load_cuisine_database(csv_path)

    # NEW: Filter cuisine database based on user preferences
    filtered_dishes = filter_cuisine_by_preferences(profile)
    cuisine_database_text = format_cuisine_for_prompt(filtered_dishes)

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
        "STRICT VARIETY RULES: No dish repeat more than 2 times in Week 1. "
        "Each day needs different breakfast/lunch/dinner. Weeks 2-4 repeat Week 1's menu."
    )
    lab_text = build_lab_value_adjustments(lab_values)
    hydration_text = "- Remind to drink 2-3 L water/day; include sleep/activity tip if relevant."
    dist_text, diet_text = build_meal_distribution_and_diet_text(diet_type, meal_freq, non_veg)
    region_text = build_region_text(region)

    prompt = assemble_prompt(
        payload, dist_text, freq_text, sub_text, skip_text, safe_text, variety_text,
        avoid_text, lab_text, hydration_text, diet_text, region_text, cuisine_database_text
    )
    return call_openai_with_retry(prompt, model)