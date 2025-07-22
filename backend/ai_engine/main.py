import sys, json
from ai_engine.planner import generate_plan
from ai_engine.pdf_generator import create_pdf, create_detailed_pdf

def load_input(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)

def validate_plan_format(plan):
    """Validate that the plan has the expected format"""
    print("\n=== Plan Validation ===")
    
    if not isinstance(plan, dict):
        print("X Plan is not a dictionary")
        return False
    
    if "7DayPlan" not in plan:
        print("X Missing '7DayPlan' key")
        return False
    
    days = plan["7DayPlan"]
    if not isinstance(days, list) or len(days) != 7:
        print(f"X '7DayPlan' should be a list of 7 days, got {len(days) if isinstance(days, list) else 'not a list'}")
        return False
    
    print(f"OK Found 7 days")
    
    # Check meal structure
    meal_count = 0
    for i, day in enumerate(days):
        day_name = day.get("Day", f"Day {i+1}")
        for meal_name, meal_data in day.items():
            if meal_name != "Day":
                meal_count += 1
                if isinstance(meal_data, dict):
                    print(f"OK {day_name} - {meal_name}: Dictionary format with {len(meal_data)} items")
                elif isinstance(meal_data, str):
                    print(f"OK {day_name} - {meal_name}: String format")
                else:
                    print(f"! {day_name} - {meal_name}: Unexpected format - {type(meal_data)}")
    
    print(f"OK Total meals found: {meal_count}")
    print("======================\n")
    return True

def run(input_path: str, output_pdf: str, format_type: str = "table"):
    # """
    # Generate diet plan and create PDF

    # Args:
    #     input_path: Path to input JSON file
    #     output_pdf: Path for output PDF
    #     format_type: "table" or "detailed"
    # """
    # print(f"Loading input from: {input_path}")
    # data = load_input(input_path)

    # print("Generating diet plan...")
    # plan = generate_plan(data)

    # if plan is None:
    #     print("❌ Diet plan generation failed. Please review the input filters or dish database.")
    #     return

    # print("\n=== Plan Structure Preview ===")
    # if "7DayPlan" in plan and len(plan["7DayPlan"]) > 0:
    #     first_day = plan["7DayPlan"][0]
    #     print(f"First day structure: {first_day.get('Day', 'Unknown')}")
    #     for meal_name, meal_data in first_day.items():
    #         if meal_name != "Day":
    #             preview = str(meal_data)[:100] + "..." if len(str(meal_data)) > 100 else str(meal_data)
    #             print(f"  {meal_name}: {preview}")
    # else:
    #     print("❗ Plan is empty or malformed. Skipping preview.")

    # print("===============================\n")

    # # Validate structure
    # validate_plan_format(plan)

    # # Create PDF
    # print(f"Creating {format_type} format PDF...")
    # if format_type.lower() == "detailed":
    #     create_detailed_pdf(plan, output_pdf)
    # else:
    #     create_pdf(plan, output_pdf)

    # print(f"✅ PDF generated at: {output_pdf}")

    # # Show summary
    # if "Summary" in plan:
    #     print("\nPlan Summary:")
    #     summary = plan["Summary"]
    #     if "AverageCalories" in summary:
    #         print(f"  Average Calories: {summary['AverageCalories']}")
    #     if "AverageMacros" in summary:
    #         macros = summary["AverageMacros"]
    #         print(f"  Macros: P:{macros.get('Protein', 'N/A')} | C:{macros.get('Carbs', 'N/A')} | F:{macros.get('Fats', 'N/A')}")

    """
    Generate diet plan and create PDF
    
    Args:
        input_path: Path to input JSON file
        output_pdf: Path for output PDF
        format_type: "table" for table format, "detailed" for detailed format
    """
    print(f"Loading input from: {input_path}")
    data = load_input(input_path)
    
    print("Generating diet plan...")
    plan = generate_plan(data)
    
    # Debug: Print the plan structure
    print("\n=== Plan Structure Preview ===")
    if "7DayPlan" in plan and len(plan["7DayPlan"]) > 0:
        first_day = plan["7DayPlan"][0]
        print(f"First day structure: {first_day.get('Day', 'Unknown')}")
        for meal_name, meal_data in first_day.items():
            if meal_name != "Day":
                preview = str(meal_data)[:100] + "..." if len(str(meal_data)) > 100 else str(meal_data)
                print(f"  {meal_name}: {preview}")
    print("===============================\n")
    
    # Validate format
    validate_plan_format(plan)
    
    # Create PDF based on format type
    print(f"Creating {format_type} format PDF...")
    if format_type.lower() == "detailed":
        create_detailed_pdf(plan, output_pdf)
    else:
        create_pdf(plan, output_pdf)
    
    print(f"OK Generated {output_pdf}")
    
    # Print summary if available
    if "Summary" in plan:
        print(f"\nPlan Summary:")
        summary = plan["Summary"]
        if "AverageCalories" in summary:
            print(f"   Average Calories: {summary['AverageCalories']}")
        if "AverageMacros" in summary:
            macros = summary["AverageMacros"]
            print(f"   Average Macros: P:{macros.get('Protein', 'N/A')} | C:{macros.get('Carbs', 'N/A')} | F:{macros.get('Fats', 'N/A')}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m ai_engine.main <input.json> <output.pdf> [format]")
        print("  format: 'table' (default) or 'detailed'")
        print("Examples:")
        print("  python -m ai_engine.main input.json output.pdf")
        print("  python -m ai_engine.main input.json output.pdf table")
        print("  python -m ai_engine.main input.json output.pdf detailed")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    pdf_format = sys.argv[3] if len(sys.argv) > 3 else "table"
    
    run(input_file, output_file, pdf_format)