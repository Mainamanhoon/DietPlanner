import os
import json
import openai
from dotenv import load_dotenv
from json import JSONDecodeError

# ─── 1. Load your API key ────────────────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in your .env file")
openai.api_key = API_KEY

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
            f"Non-Veg: only eggs, chicken or fish allowed (no shrimp/oysters/shellfish/turkey); "
            f"limit to one animal-protein meal per day on {non_veg}. "
            "If suggesting a fish dish, also provide a chicken alternative separated by '/'."
        )
    elif dt == "eggetarian":
        diet_text = "Eggetarian: Only are veg and eggs are allowed."
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
    else:
        return "Mixed cuisine."

def assemble_prompt(payload, dist_text, freq_text, sub_text, skip_text, safe_text, variety_text, avoid_text, lab_text, hydration_text, diet_text, region_text):
    payload_str = json.dumps(payload, indent=2)
    prompt = f"""
You are a certified dietitian. Given this JSON payload:
{payload_str}

**Meal Distribution**:
{dist_text}

**Ingredient Frequency Constraints**:
{freq_text}

**Dislikes & Substitutions**:
{sub_text}

**Meal Timing/Skipping**:
{skip_text}

**Safe Defaults**:
{safe_text}

**Variety & Repetition**:
{variety_text}

**Health Condition Avoidances**:
{avoid_text}

**Lab-Value Nutrient Adjustments**:
{lab_text}

**Hydration & Other Advice**:
{hydration_text}

**Dietary Preferences**:
{diet_text}

**Regional/Cultural Preference**:
{region_text}

Generate a **7-day** diet plan (to repeat for 4 weeks) with **no repeated dishes** in Week 1.
Return **ONLY** valid JSON, with exactly 7 entries under "7DayPlan":
{{
  "7DayPlan": [ /* 7 day-objects Day 1 to Day 7 */ ],
  "Summary": {{
    "AverageCalories": "### kcal/day",
    "AverageMacros": {{ "Protein":"##g","Carbs":"##g","Fats":"##g" }}
  }}
}}
"""
    return prompt

def call_openai_with_retry(prompt, model):
    last_clean = None
    for attempt in range(1, 4):
        resp = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role":"system","content":"You return only valid JSON diet plans."},
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

def get_diet_plan_via_gpt(payload: dict, model: str = "gpt-4") -> dict:
    profile     = payload.get("user_profile", {})
    diet_type   = profile.get("Diet type", "Mixed")
    meal_freq   = int(profile.get("Meal frequency in a day", 3))
    non_veg     = profile.get("Non-Veg Days", [])
    conditions  = profile.get("Health Conditions", [])
    region      = profile.get("Culture preference", "Mixed")
    freq_cons   = profile.get("Ingredient Frequency", {})
    dislikes    = profile.get("Dislikes", [])
    lab_values  = profile.get("Lab Values", {})

    avoid_text = build_health_avoidance(conditions)
    freq_text = build_ingredient_frequency(freq_cons)
    sub_text = build_dislikes_substitutions(dislikes)
    skip_text = (
        "If meal frequency <3, omit Breakfast and redistribute its calories. "
        "If user skips Dinner, redistribute dinner calories to other meals/snacks."
    )
    safe_text = (
        "If activity level or metrics are missing, assume lightly active (×1.375) "
        "and note “assuming lightly active lifestyle.”"
    )
    variety_text = (
        "No dish repeat within Week 1. Weeks 2–4 repeat Week 1's menu unless user requests more variety."
    )
    lab_text = build_lab_value_adjustments(lab_values)
    hydration_text = "- Remind to drink 2–3 L water/day; include sleep/activity tip if relevant."
    dist_text, diet_text = build_meal_distribution_and_diet_text(diet_type, meal_freq, non_veg)
    region_text = build_region_text(region)

    prompt = assemble_prompt(
        payload, dist_text, freq_text, sub_text, skip_text, safe_text, variety_text,
        avoid_text, lab_text, hydration_text, diet_text, region_text
    )
    return call_openai_with_retry(prompt, model)
