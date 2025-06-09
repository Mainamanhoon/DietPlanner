# ai_engine/main.py
import json, sys
from .planner import generate_plan
from .pdf_generator import create_pdf

def load_input(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)

def run(input_path: str, output_pdf: str):
    data = load_input(input_path)
    plan = generate_plan(data)
    create_pdf(plan, output_pdf)
    print(f"✅ Generated {output_pdf}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python -m ai_engine.main <input.json> <output.pdf>")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2])
