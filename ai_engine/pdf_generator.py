# ai_engine/pdf_generator.py

import math
from fpdf import FPDF

def create_pdf(plan: dict, filename: str):
    """
    Render the 7-day plan as a neat landscape table with:
      - Columns: Day | [meals in the exact order they appear in the JSON]
      - Wrapped text, padding, dynamic row heights
    """
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Personalized 7-Day Diet Plan", ln=True, align="C")
    pdf.ln(5)

    # --- Determine meal columns in JSON order ---
    meal_keys = []
    for entry in plan.get("7DayPlan", []):
        # entry is a dict: first key is "Day", subsequent keys are meals in order received
        for key in entry:
            if key != "Day" and key not in meal_keys:
                meal_keys.append(key)
    headers    = ["Day"] + meal_keys

    # --- Compute column widths to fill the page ---
    total_w    = pdf.w - pdf.l_margin - pdf.r_margin  # usable width
    col_count  = len(headers)
    col_width  = total_w / col_count

    # Draw header row
    pdf.set_font("Helvetica", "B", 12)
    for h in headers:
        pdf.cell(col_width, 10, h, border=1, align="C")
    pdf.ln()

    # Body settings
    padding     = 3    # mm inside each cell
    line_height = 5    # mm per line
    left_margin = pdf.l_margin
    pdf.set_font("Helvetica", "", 10)

    # Draw each day's row
    for entry in plan.get("7DayPlan", []):
        # Build cell texts in header order
        cells = [entry.get("Day", "")]
        for key in meal_keys:
            cells.append(entry.get(key, ""))

        # Compute needed lines per cell
        line_counts = []
        for idx, text in enumerate(cells):
            usable_w = col_width - 2*padding
            text_w   = pdf.get_string_width(text)
            lines    = max(1, math.ceil(text_w / usable_w))
            line_counts.append(lines)

        # Row height = tallest cell
        max_lines = max(line_counts)
        row_h     = max_lines * line_height + 2 * padding

        # Draw cell borders
        x = left_margin
        y = pdf.get_y()
        for _ in headers:
            pdf.rect(x, y, col_width, row_h)
            x += col_width

        # Fill cell text
        x = left_margin
        for idx, text in enumerate(cells):
            pdf.set_xy(x + padding, y + padding)
            pdf.multi_cell(
                w      = col_width - 2*padding,
                h      = line_height,
                txt    = text,
                border = 0
            )
            x += col_width

        # Move to next row
        pdf.set_y(y + row_h)

    # Save PDF
    pdf.output(filename)
