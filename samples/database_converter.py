import csv
import json

def convert_csv_to_database():
    """
    Convert your CSV file to Python database format
    CSV columns: Name, State/Region, Quantity, Calories, Protein, Carbs, Fat, Veg/Non-Veg, Meal Type, Ingredients
    """
    
    database = []
    
    # If you have a CSV file, use this:
    with open('your_cuisine_data.csv', 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            dish = {
                "name": row['Name'].strip(),
                "region": row['State/Region'].strip(),
                "quantity": row['Quantity'].strip(),
                "calories": int(row['Calories (kcal)']),
                "protein": int(row['Protein (g)']),
                "carbs": int(row['Carbs (g)']),
                "fat": int(row['Fat (g)']),
                "veg_type": row['Veg/Non-Veg'].strip(),
                "meal_type": row['Meal Type'].strip(),
                "ingredients": row['Ingredients'].strip()
            }
            database.append(dish)
    
    # Print the formatted database for copying into your code
    print("CUISINE_DATABASE = [")
    for i, dish in enumerate(database):
        print(f"    {json.dumps(dish, indent=4)}", end="")
        if i < len(database) - 1:
            print(",")
        else:
            print("")
    print("]")

# Or manually add a few examples:
sample_database = [
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
    },
    # Add your other 39 dishes here...
]

if __name__ == "__main__":
    # Uncomment the method you want to use:
    # convert_csv_to_database()  # If you have CSV
    
    # Or print sample format:
    print("Sample database format:")
    print(json.dumps(sample_database, indent=2))