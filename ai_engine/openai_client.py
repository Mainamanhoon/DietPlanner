import os
import openai
import json
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in .env")
openai.api_key = API_KEY

# def get_diet_plan_via_gpt(user_data: dict, model: str = "gpt-4.1") -> dict:
#     """
#     Sends the user_data JSON to GPT-4.1 and returns a parsed JSON diet plan.
#     """
#     prompt = f"""
# You are a certified dietitian. Given this JSON of user survey answers:
# This is for Indian Deit plan so make it accordingly.
# {user_data}

# Return only valid JSON with:
# - "Total Calories": "<number> kcal/day"
# - "Meals": {{
#     "Breakfast": {{ "description": str, "calories": "<number> kcal" }},
#     "Lunch":     {{ ... }},
#     "Dinner":    {{ ... }}
# }}
# """
#     resp = openai.ChatCompletion.create(
#         model=model,
#         messages=[
#             {"role": "system",  "content": "You are a helpful diet-plan generator."},
#             {"role": "user",    "content": prompt}
#         ],
#         temperature=0.7,
#         max_tokens=500
#     )
#     text = resp.choices[0].message.content.strip()
#     return json.loads(text)
 

 

def get_diet_plan_via_gpt(payload: dict, model: str = "gpt-4") -> dict:
    """
    Sends the user_data JSON to GPT-4 and returns a parsed JSON diet plan.
    """
    prompt = f"""
You are a certified dietitian. Given this user profile and computed metrics:
{json.dumps(payload, indent=2)}

Generate a 7-day Indian diet plan. Return ONLY valid JSON with this exact structure:
{{
    "7DayPlan": [
        {{
            "day": "Day 1",
            "Meals": {{
                "Breakfast": {{ "description": "Meal description (calories)", "calories": "300 kcal" }},
                "Lunch": {{ "description": "Meal description (calories)", "calories": "500 kcal" }},
                "Dinner": {{ "description": "Meal description (calories)", "calories": "400 kcal" }}
            }}
        }},
        // ... repeat for days 2-7
    ],
    "Summary": {{
        "AverageCalories": "1200 kcal/day",
        "Macros": {{
            "Carbs": "150g",
            "Protein": "80g",
            "Fats": "40g"
        }}
    }}
}}

Important:
1. Make meals appropriate for Indian cuisine
2. Include calories in parentheses in the description
3. Ensure all 7 days are present
4. Return ONLY the JSON, no other text
"""
    resp = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful diet-plan generator that returns only valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=2000
    )
    text = resp.choices[0].message.content.strip()
    return json.loads(text)
