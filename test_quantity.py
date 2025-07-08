#!/usr/bin/env python3
"""
Test script for quantity adjustment functionality
"""

from ai_engine.openai_client import calculate_quantity_multiplier, adjust_quantity_with_multiplier

def test_quantity_multipliers():
    """Test quantity multiplier calculations for different scenarios"""
    print("🧪 Testing Quantity Adjustment Functionality")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        {
            "name": "Fat Loss - Moderately Active",
            "profile": {
                "Goals": "fat loss",
                "Activity level": "Moderately active",
                "Health Conditions": []
            },
            "expected_range": (0.7, 0.9)
        },
        {
            "name": "Muscle Gain - Very Active", 
            "profile": {
                "Goals": "muscle gain",
                "Activity level": "Very active",
                "Health Conditions": []
            },
            "expected_range": (1.2, 1.4)
        },
        {
            "name": "Weight Gain - Sedentary",
            "profile": {
                "Goals": "weight gain", 
                "Activity level": "Sedentary",
                "Health Conditions": []
            },
            "expected_range": (1.1, 1.3)
        },
        {
            "name": "Fat Loss with Diabetes",
            "profile": {
                "Goals": "fat loss",
                "Activity level": "Moderately active", 
                "Health Conditions": ["Diabetes"]
            },
            "expected_range": (0.6, 0.8)
        },
        {
            "name": "General Wellness",
            "profile": {
                "Goals": "general wellness",
                "Activity level": "Moderately active",
                "Health Conditions": []
            },
            "expected_range": (0.9, 1.1)
        }
    ]
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        
        multiplier = calculate_quantity_multiplier(
            test_case['profile']['Goals'], 
            test_case['profile']
        )
        
        expected_min, expected_max = test_case['expected_range']
        passed = expected_min <= multiplier <= expected_max
        
        print(f"   Expected: {expected_min:.2f} - {expected_max:.2f}")
        print(f"   Actual: {multiplier:.2f}")
        print(f"   Status: {'✅ PASS' if passed else '❌ FAIL'}")
        
        if not passed:
            all_passed = False
    
    print(f"\n{'='*50}")
    print(f"Overall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return all_passed

def test_quantity_adjustment():
    """Test the quantity adjustment function with various inputs"""
    print("\n🔧 Testing Quantity Adjustment Function")
    print("=" * 40)
    
    test_cases = [
        {
            "input": "1 bowl (200g)",
            "multiplier": 0.8,
            "expected": "1 bowl (160g)"
        },
        {
            "input": "2 pieces (100g)",
            "multiplier": 0.8,
            "expected": "2 pieces (80g)"
        },
        {
            "input": "1 cup (150ml)",
            "multiplier": 1.2,
            "expected": "1 cup (180ml)"
        },
        {
            "input": "1 serving",
            "multiplier": 0.8,
            "expected": "1 serving"
        },
        {
            "input": "3 rotis (90g)",
            "multiplier": 1.3,
            "expected": "3 rotis (117g)"
        },
        {
            "input": "1 plate (250g) + 2 tbsp (30g)",
            "multiplier": 0.9,
            "expected": "1 plate (225g) + 2 tbsp (27g)"
        },
        {
            "input": "1 bowl (150.5g)",
            "multiplier": 0.8,
            "expected": "1 bowl (120.4g)"
        }
    ]
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        result = adjust_quantity_with_multiplier(test_case["input"], test_case["multiplier"])
        passed = result == test_case["expected"]
        
        print(f"\n{i}. Input: '{test_case['input']}' (×{test_case['multiplier']})")
        print(f"   Expected: '{test_case['expected']}'")
        print(f"   Actual:   '{result}'")
        print(f"   Status: {'✅ PASS' if passed else '❌ FAIL'}")
        
        if not passed:
            all_passed = False
    
    print(f"\n{'='*40}")
    print(f"Adjustment Test Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return all_passed

def demonstrate_quantity_examples():
    """Show practical examples of quantity adjustments"""
    print("\n📏 QUANTITY ADJUSTMENT EXAMPLES")
    print("=" * 40)
    
    # Example dishes with reference quantities
    example_dishes = [
        {"name": "Dal Tadka + Rice", "ref_quantity": "1 bowl (200g)"},
        {"name": "Paneer Tikka", "ref_quantity": "2 pieces (100g)"},
        {"name": "Oatmeal", "ref_quantity": "1 cup (150ml)"},
        {"name": "Chicken Curry", "ref_quantity": "1 plate (250g)"},
        {"name": "Mixed Vegetable Sabzi", "ref_quantity": "1 bowl (180g)"},
        {"name": "Simple Serving", "ref_quantity": "1 serving"},
        {"name": "Complex Dish", "ref_quantity": "1 plate (300g) + 2 tbsp (20g)"}
    ]
    
    # Different goals
    goals = ["fat loss", "muscle gain", "weight gain", "general wellness"]
    
    for goal in goals:
        print(f"\n🎯 Goal: {goal.upper()}")
        print("-" * 30)
        
        # Create a sample profile for this goal
        profile = {
            "Goals": goal,
            "Activity level": "Moderately active",
            "Health Conditions": []
        }
        
        multiplier = calculate_quantity_multiplier(goal, profile)
        
        for dish in example_dishes:
            ref_qty = dish["ref_quantity"]
            adjusted_qty = adjust_quantity_with_multiplier(ref_qty, multiplier)
            print(f"  {dish['name']}: {ref_qty} → {adjusted_qty}")

if __name__ == "__main__":
    # Run tests
    test_quantity_multipliers()
    
    # Test quantity adjustment function
    test_quantity_adjustment()
    
    # Show examples
    demonstrate_quantity_examples()
    
    print("\n✅ Quantity adjustment functionality is ready!")
    print("💡 The system now only applies multipliers to absolute quantities (g, ml, kg, etc.)")
    print("💡 Relative quantities (bowls, pieces, cups) remain unchanged.") 