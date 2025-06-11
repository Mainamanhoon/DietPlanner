# ai_engine/pdf_generator.py

import math
from fpdf import FPDF

def create_pdf(plan: dict, filename: str):
    """
    Render the 7-day plan as a neat landscape table with:
      - Columns: Day | [Dynamic meal columns]
      - Wrapped text, padding, dynamic row heights
      - Handles any number of meals per day (3-5)
    """
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Personalized 7-Day Diet Plan", ln=True, align="C")
    pdf.ln(5)

    # --- Dynamically determine meal columns ---
    meal_keys = set()
    for entry in plan.get("7DayPlan", []):
        for key in entry.keys():
            if key.lower() != "day":
                meal_keys.add(key)
    meal_keys = sorted(meal_keys)  # e.g., ['Breakfast', 'Dinner', 'Lunch', 'Snacks']

    headers = ["Day"] + meal_keys
    col_count = len(headers)
    col_width = 280 / col_count  # Adjust to fit your page width

    # Draw headers
    pdf.set_font("Helvetica", "B", 12)
    for h in headers:
        pdf.cell(col_width, 10, h, border=1, align="C")
    pdf.ln()

    # Body settings
    padding     = 3    # mm
    line_h      = 5    # mm per text line
    left_margin = pdf.l_margin
    pdf.set_font("Helvetica", "", 10)

    for entry in plan.get("7DayPlan", []):
        cells = [entry.get("Day", "")] + [entry.get(key, "") for key in meal_keys]

        # Compute needed lines per cell
        line_counts = []
        for text in cells:
            usable_w = col_width - 2 * padding
            text_w   = pdf.get_string_width(text)
            lines    = max(1, math.ceil(text_w / usable_w))
            line_counts.append(lines)

        # Row height
        max_lines = max(line_counts)
        row_h     = max_lines * line_h + 2 * padding

        # Draw cell borders
        x = left_margin
        y = pdf.get_y()
        for _ in headers:
            pdf.rect(x, y, col_width, row_h)
            x += col_width

        # Fill text
        x = left_margin
        for idx, text in enumerate(cells):
            pdf.set_xy(x + padding, y + padding)
            pdf.multi_cell(
                w    = col_width - 2 * padding,
                h    = line_h,
                txt  = text,
                border = 0
            )
            x += col_width

        # Next row
        pdf.set_y(y + row_h)

    pdf.output(filename)
