# ai_engine/openai_client.py

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

def get_diet_plan_via_gpt(payload: dict, model: str = "gpt-4") -> dict:
    """
    Sends the payload to GPT-4 with all personalization rules,
    retries up to 3 times to ensure exactly 7 days in the plan,
    and returns the parsed JSON diet plan.
    """
    # ─── 2. Unpack user profile ───────────────────────────────────────────────
    profile     = payload.get("user_profile", {})
    diet_type   = profile.get("Diet type", "Mixed")
    meal_freq   = int(profile.get("Meal frequency in a day", 3))
    non_veg     = profile.get("Non-Veg Days", [])
    conditions  = profile.get("Health Conditions", [])
    region      = profile.get("Culture preference", "Mixed")

    # new fields for ingredient/frequency, dislikes, labs:
    freq_cons   = profile.get("Ingredient Frequency", {})  # e.g. {"chicken":3,"fish":2}
    dislikes    = profile.get("Dislikes", [])               # e.g. ["broccoli","mushrooms"]
    lab_values  = profile.get("Lab Values", {})             # e.g. {"Vitamin B12":"low", "Triglycerides":"high"}

    # ─── 3. Build Health-Condition Avoidance text ─────────────────────────────
    avoid_rules = []
    for cond in conditions:
        lc = cond.lower()
        if lc == "diabetes":
            avoid_rules.append("- Diabetes: avoid refined sugars, sweets, white bread/rice, high-GI carbs.")
        elif lc == "pcos":
            avoid_rules.append("- PCOS: avoid dairy & gluten; use gluten-free or dairy-free swaps.")
        elif lc == "thyroid":
            avoid_rules.append("- Thyroid: avoid raw crucifers (broccoli, kale), soy, goitrogens; cooked OK.")
    avoid_text = "\n".join(avoid_rules) if avoid_rules else "- None."

    # ─── 4. Ingredient-Frequency Constraints ──────────────────────────────────
    if freq_cons:
        freq_text = "\n".join(
            f"- Use {ing} ~{cnt}x/week, spaced out (not back-to-back)."
            for ing, cnt in freq_cons.items()
        )
    else:
        freq_text = "- None specified."

    # ─── 5. Dislikes & Substitutions ─────────────────────────────────────────
    if dislikes:
        sub_text = "\n".join(
            f"- Exclude {item}; substitute with similar nutrient-dense alternatives."
            for item in dislikes
        )
    else:
        sub_text = "- None."

    # ─── 6. Meal Timing / Skipping ────────────────────────────────────────────
    skip_text = (
        "If meal frequency <3, omit Breakfast and redistribute its calories. "
        "If user skips Dinner, redistribute dinner calories to other meals/snacks."
    )

    # ─── 7. Safe Defaults ──────────────────────────────────────────────────────
    safe_text = (
        "If activity level or metrics are missing, assume lightly active (×1.375) "
        "and note “assuming lightly active lifestyle.”"
    )

    # ─── 8. Variety & Repetition ───────────────────────────────────────────────
    variety_text = (
        "No dish repeat within Week 1. Weeks 2–4 repeat Week 1’s menu unless user requests more variety."
    )

    # ─── 9. Lab-Value Nutrient Adjustments ────────────────────────────────────
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
    lab_text = "\n".join(lab_lines) if lab_lines else "- None."

    # ─── 10. Hydration & Other Advice ──────────────────────────────────────────
    hydration_text = "- Remind to drink 2–3 L water/day; include sleep/activity tip if relevant."

    # ─── 11. Meal Distribution & Diet/Region ─────────────────────────────────
    snack_ct = max(0, meal_freq - 3)
    dist_text = (
        f"Breakfast:20–25%, Lunch:30–35%, Dinner:30–35%, "
        f"Snacks:5–10% ({snack_ct} snack{'s' if snack_ct!=1 else ''}); redistribute if skipped."
    )
    dt = diet_type.lower()
    if dt == "non-vegetarian":
        diet_text = f"Non-Veg: limit animal protein to 1 meal/day, on {non_veg}."
    elif dt == "eggetarian":
        diet_text = "Eggetarian: no meat/fish; eggs allowed."
    elif dt == "jain":
        diet_text = "Jain: no eggs, root veg, honey, gelatin; use asafoetida."
    elif dt == "vegetarian":
        diet_text = "Vegetarian: no meat, fish, or eggs."
    else:
        diet_text = "Mixed: veg + non-veg allowed."
    rp = region.lower()
    if "north" in rp:
        region_text = "North Indian: rotis, dals, sabzis, paneer, curd."
    elif "south" in rp:
        region_text = "South Indian: rice/idli, dosa, upma, sambar."
    elif "western" in rp:
        region_text = "Western: oatmeal, salads, grilled proteins."
    else:
        region_text = "Mixed cuisine."

    # ─── 12. Build the prompt once ────────────────────────────────────────────
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

    # ─── 13. Retry loop to enforce 7 days ─────────────────────────────────────
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
    # after 3 attempts, error
    raise ValueError(f"Failed to get exactly 7 days after 3 attempts. Last response:\n{last_clean}")
