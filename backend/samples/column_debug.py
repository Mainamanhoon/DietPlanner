import pandas as pd
import sys

def debug_columns(csv_path="samples/CuisineList.csv"):
    print(f"=== DEBUGGING COLUMNS IN: {csv_path} ===\n")
    
    try:
        df = pd.read_csv(csv_path)
        
        print(f"📋 Total columns found: {len(df.columns)}\n")
        
        print("🔍 EXACT column names (with quotes to show spaces):")
        for i, col in enumerate(df.columns):
            print(f"   {i+1}. '{col}'")
            # Show length and any hidden characters
            print(f"      Length: {len(col)}")
            if col != col.strip():
                print(f"      ⚠️  Has extra spaces! Stripped: '{col.strip()}'")
        
        print(f"\n📊 Required columns:")
        required_cols = [
            'Name', 'State/Region', 'Quantity', 'Calories (kcal)', 
            'Protein (g)', 'Carbs (g)', 'Fat (g)', 'Veg/Non-Veg', 
            'Meal Type', 'Ingredients'
        ]
        
        for req_col in required_cols:
            if req_col in df.columns:
                print(f"   ✅ '{req_col}' - FOUND")
            else:
                print(f"   ❌ '{req_col}' - MISSING")
                # Try to find similar columns
                similar = [col for col in df.columns if req_col.lower() in col.lower()]
                if similar:
                    print(f"      🔍 Similar columns found: {similar}")
        
        print(f"\n📝 First row of data:")
        if len(df) > 0:
            for col in df.columns:
                print(f"   {col}: {df.iloc[0][col]}")
        
        # Check for common issues
        print(f"\n🔧 Common fixes:")
        print("   1. Remove extra spaces from column names")
        print("   2. Check exact spelling and capitalization")
        print("   3. Open CSV in text editor to see raw headers")
        
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")

if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "samples/CuisineList.csv"
    debug_columns(csv_path)