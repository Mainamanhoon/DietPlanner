# ai_engine/pdf_generator.py
import json
import logging
from fpdf import FPDF

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def create_pdf(plan: dict, filename: str):
    """
    Render the 7-day diet plan in a tabular PDF with columns: Day, Breakfast, Lunch, Dinner.
    Supports both list and dict formats for "7DayPlan".
    """
    # Log the plan data once before generating PDF
    logger.debug("Diet plan data:\n%s", json.dumps(plan, indent=2))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Personalized 7-Day Diet Plan", ln=1, align="C")
    pdf.ln(5)

    # Table header
    pdf.set_font("Arial", "B", 12)
    col_widths = [30, 60, 60, 60]
    headers = ["Day", "Breakfast", "Lunch", "Dinner"]
    for idx, header in enumerate(headers):
        pdf.cell(col_widths[idx], 10, header, border=1, align="C")
    pdf.ln()

    # Extract day entries
    raw_days = plan.get("7DayPlan")
    if isinstance(raw_days, list):
        days_list = raw_days
    elif isinstance(raw_days, dict):
        days_list = [{"day": day, **data} for day, data in raw_days.items()]
    else:
        days_list = []

    # Table rows
    pdf.set_font("Arial", size=10)
    for entry in days_list:
        day_label = entry.get("day", "-")
        meals = entry.get("Meals") or entry.get("meals") or {}

        def brief(meal_name: str) -> str:
            item = meals.get(meal_name) or meals.get(meal_name.lower(), {})
            desc = item.get("description", "")
            return desc.split(",")[0].split("(")[0].strip() if desc else "-"

        row = [
            day_label,
            brief("Breakfast"),
            brief("Lunch"),
            brief("Dinner")
        ]
        for idx, text in enumerate(row):
            pdf.cell(col_widths[idx], 10, text, border=1)
        pdf.ln()

    # Save PDF file
    pdf.output(filename)
