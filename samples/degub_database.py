# debug_database.py - Run this to check what's happening

import json
from ai_engine.openai_client import load_cuisine_database, filter_cuisine_by_preferences, format_cuisine_for_prompt

def debug_database():
    print("=== DEBUGGING CUISINE DATABASE ===\n")
    
    # 1. Check if CSV loads
    print("1. Loading database...")
    database = load_cuisine_database("samples/CuisineList.csv")
    print(f"   Total dishes loaded: {len(database)}")
    
    if len(database) <= 1:
        print("   ❌ PROBLEM: Only 1 dish found! Check your CSV file.")
        return
    
    # 2. Show first few dishes
    print("\n2. First 3 dishes in database:")
    for i, dish in enumerate(database[:3]):
        print(f"   {i+1}. {dish['name']} ({dish['meal_type']}) - {dish['veg_type']}")
    
    # 3. Check meal type distribution
    breakfast_count = sum(1 for d in database if "Breakfast" in d['meal_type'])
    lunch_dinner_count = sum(1 for d in database if "Lunch" in d['meal_type'] or "Dinner" in d['meal_type'])
    
    print(f"\n3. Meal type distribution:")
    print(f"   Breakfast dishes: {breakfast_count}")
    print(f"   Lunch/Dinner dishes: {lunch_dinner_count}")
    
    # 4. Test filtering with sample user profile
    print("\n4. Testing with sample user profile...")
    sample_profile = {
        "Diet type": "Vegetarian",
        "Culture preference": "Mixed", 
        "Health Conditions": [],
        "Dislikes": []
    }
    
    filtered = filter_cuisine_by_preferences(sample_profile)
    print(f"   Dishes after filtering: {len(filtered)}")
    
    if len(filtered) <= 3:
        print("   ❌ PROBLEM: Too few dishes after filtering!")
        print("   Available dishes:")
        for dish in filtered:
            print(f"     - {dish['name']} ({dish['meal_type']})")
    else:
        print("   ✅ Good: Enough variety available")
    
    # 5. Show what GPT would see
    print("\n5. Sample of what GPT receives:")
    cuisine_text = format_cuisine_for_prompt(filtered[:10])  # Show first 10
    print(cuisine_text[:500] + "..." if len(cuisine_text) > 500 else cuisine_text)

if __name__ == "__main__":
    debug_database()