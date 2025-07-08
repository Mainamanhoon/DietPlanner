import sys, json
from ai_engine.planner     import generate_plan
from ai_engine.pdf_generator import create_pdf
from ai_engine.openai_client import calculate_quantity_multiplier

def load_input(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)

def run(input_path: str, output_pdf: str, csv_path: str = "samples/CuisineList.csv"):
    data = load_input(input_path)
    plan = generate_plan(data, csv_path)
    # Debug: Print the plan structure
    print("\n=== Plan Structure ===")
    print(json.dumps(plan, indent=2))
    print("=====================\n")
    create_pdf(plan, output_pdf)
    print(f"✅ Generated {output_pdf}")

def demonstrate_quantity_adjustment():
    """Demonstrate how quantity adjustment works for different goals"""
    print("=== QUANTITY ADJUSTMENT DEMONSTRATION ===\n")
    
    # Sample user profiles for different goals
    sample_profiles = [
        {
            "Name of the employee": "John",
            "Age": "25",
            "Gender": "Male", 
            "Weight & Height": "70kg, 175cm",
            "Activity level": "Moderately active",
            "Goals": "fat loss",
            "Diet type": "Vegetarian",
            "Meal frequency in a day": "3",
            "Non-Veg Days": [],
            "Health Conditions": [],
            "Culture preference": "Mixed",
            "Any food allergies": "",
            "Lab Values": {},
            "Dislikes": [],
            "Ingredient Frequency": {}
        },
        {
            "Name of the employee": "Sarah",
            "Age": "28",
            "Gender": "Female",
            "Weight & Height": "55kg, 160cm", 
            "Activity level": "Very active",
            "Goals": "muscle gain",
            "Diet type": "Eggetarian",
            "Meal frequency in a day": "4",
            "Non-Veg Days": [],
            "Health Conditions": [],
            "Culture preference": "North Indian",
            "Any food allergies": "",
            "Lab Values": {},
            "Dislikes": [],
            "Ingredient Frequency": {}
        },
        {
            "Name of the employee": "Mike",
            "Age": "30",
            "Gender": "Male",
            "Weight & Height": "65kg, 180cm",
            "Activity level": "Sedentary", 
            "Goals": "weight gain",
            "Diet type": "Non-vegetarian",
            "Meal frequency in a day": "3",
            "Non-Veg Days": ["Monday", "Wednesday", "Friday"],
            "Health Conditions": [],
            "Culture preference": "Mixed",
            "Any food allergies": "",
            "Lab Values": {},
            "Dislikes": [],
            "Ingredient Frequency": {}
        }
    ]
    
    for i, profile in enumerate(sample_profiles, 1):
        goal = profile["Goals"]
        multiplier = calculate_quantity_multiplier(goal, profile)
        
        print(f"Profile {i}: {profile['Name of the employee']} - {goal.upper()}")
        print(f"  Activity: {profile['Activity level']}")
        print(f"  Quantity Multiplier: {multiplier}x")
        print(f"  Example adjustments:")
        print(f"    - 1 bowl (200g) → {multiplier:.1f} bowl ({int(200*multiplier)}g)")
        print(f"    - 2 pieces (100g) → {multiplier*2:.1f} pieces ({int(100*multiplier)}g)")
        print(f"    - 1 cup (150g) → {multiplier:.1f} cup ({int(150*multiplier)}g)")
        print()

def demo_quantity_feature():
    """Demo the quantity adjustment feature"""
    print("🍽️  Wellnetic Diet Plan Generator - Quantity Adjustment Demo")
    print("=" * 60)
    
    # Demonstrate quantity adjustment
    demonstrate_quantity_adjustment()
    
    # Sample user data
    user_data = {
        "Name of the employee": "Test User",
        "Age": "25",
        "Gender": "Male",
        "Weight & Height": "70kg, 175cm",
        "Activity level": "Moderately active",
        "Goals": "fat loss",  # Try different goals: "fat loss", "muscle gain", "weight gain", "general wellness"
        "Diet type": "Vegetarian",
        "Meal frequency in a day": "3",
        "Non-Veg Days": [],
        "Health Conditions": [],
        "Culture preference": "Mixed",
        "Any food allergies": "",
        "Lab Values": {},
        "Dislikes": [],
        "Ingredient Frequency": {}
    }
    
    print(f"📋 Generating plan for: {user_data['Name of the employee']}")
    print(f"🎯 Goal: {user_data['Goals']}")
    print(f"🥗 Diet: {user_data['Diet type']}")
    
    # Calculate and show quantity multiplier
    multiplier = calculate_quantity_multiplier(user_data['Goals'], user_data)
    print(f"📏 Quantity multiplier: {multiplier}x")
    print()
    
    try:
        # Generate plan
        plan = generate_plan(user_data)
        
        # Save as JSON
        with open("diet_plan.json", "w") as f:
            json.dump(plan, f, indent=2)
        print("✅ Plan saved as diet_plan.json")
        
        # Generate PDF
        create_pdf(plan, "output.pdf")
        print("✅ PDF saved as output.pdf")
        
        # Show summary
        summary = plan.get("Summary", {})
        print(f"\n📊 Plan Summary:")
        print(f"   Average Calories: {summary.get('AverageCalories', 'N/A')}")
        avg_macros = summary.get('AverageMacros', {})
        print(f"   Average Protein: {avg_macros.get('Protein', 'N/A')}")
        print(f"   Average Carbs: {avg_macros.get('Carbs', 'N/A')}")
        print(f"   Average Fats: {avg_macros.get('Fats', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error generating plan: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Run demo if no arguments provided
        demo_quantity_feature()
    elif len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python -m ai_engine.main [<input.json> <output.pdf> [CuisineList.csv]]")
        print("       python -m ai_engine.main  # Run demo")
        sys.exit(1)
    else:
        # Run with arguments
        input_path = sys.argv[1]
        output_pdf = sys.argv[2]
        csv_path = sys.argv[3] if len(sys.argv) == 4 else "samples/CuisineList.csv"
        
        run(input_path, output_pdf, csv_path)