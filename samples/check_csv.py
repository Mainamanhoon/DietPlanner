# check_csv.py - Quick CSV file checker

import pandas as pd
import os

def check_csv_file(csv_path="samples/CuisineList.csv"):
    print(f"=== CHECKING CSV FILE: {csv_path} ===\n")
    
    # Check if file exists
    if not os.path.exists(csv_path):
        print(f"❌ File '{csv_path}' does not exist!")
        print("   Create the file or use a different path.")
        return
    
    try:
        # Load CSV
        df = pd.read_csv(csv_path)
        print(f"✅ File loaded successfully!")
        print(f"   Rows: {len(df)}")
        print(f"   Columns: {len(df.columns)}")
        
        # Check required columns
        required_cols = [
            'Name', 'State/Region', 'Quantity', 'Calories (kcal)', 
            'Protein (g)', 'Carbs (g)', 'Fat (g)', 'Veg/Non-Veg', 
            'Meal Type', 'Ingredients'
        ]
        
        print(f"\n📋 Column check:")
        missing_cols = []
        for col in required_cols:
            if col in df.columns:
                print(f"   ✅ {col}")
            else:
                print(f"   ❌ {col} - MISSING!")
                missing_cols.append(col)
        
        if missing_cols:
            print(f"\n⚠️  Missing columns: {missing_cols}")
            print("   Available columns:", list(df.columns))
            return
        
        # Show sample data
        print(f"\n📊 Sample dishes:")
        for i in range(min(3, len(df))):
            row = df.iloc[i]
            print(f"   {i+1}. {row['Name']} ({row['Meal Type']}) - {row['Veg/Non-Veg']}")
        
        # Check meal type distribution
        meal_types = df['Meal Type'].value_counts()
        print(f"\n🍽️  Meal type distribution:")
        for meal_type, count in meal_types.items():
            print(f"   {meal_type}: {count}")
        
        # Check diet type distribution  
        diet_types = df['Veg/Non-Veg'].value_counts()
        print(f"\n🥗 Diet type distribution:")
        for diet_type, count in diet_types.items():
            print(f"   {diet_type}: {count}")
            
        print(f"\n✅ CSV file looks good! Ready to use.")
        
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")

if __name__ == "__main__":
    import sys
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "samples/CuisineList.csv"
    check_csv_file(csv_path)