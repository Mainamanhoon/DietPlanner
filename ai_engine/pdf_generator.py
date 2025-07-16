# ─── ai_engine/pdf_generator.py ────────────────────────────────────────────
import math
import re
from decimal import Decimal, ROUND_HALF_UP
from fpdf import FPDF

import re
from decimal import Decimal, ROUND_HALF_UP


#  helper ────────────────────────────────────────────────────────
def _pretty_qty(raw: str) -> str:
    """
    Round every numeric component in a quantity string.

        "1.68 medium bowl"               → "1.5 medium bowl"
        "4.62 rotis + 1.38 bowl"         → "5 rotis + 1.5 bowl"
        "0.37 tsp + 0.37 piece + 0.37 g" → "0.5 tsp + 1 piece + 0.5 g"

    Rules
    -----
    • Bread-like units (roti, paratha, puri, chapati, bhatura, piece/pcs/serving)
      are rounded to the nearest whole integer, minimum 1.
    • All other units are rounded to the nearest 0 .5.
    """
    if not isinstance(raw, str):
        return str(raw)

    # Split on “+” so every component is handled separately
    parts = [p.strip() for p in raw.split("+")]

    whole_units = {
        "roti", "rotis", "chapati", "chapatis",
        "paratha", "parathas", "puri", "puris",
        "bhatura", "bhaturas",
        "piece", "pieces", "pc", "pcs",
        "serving", "servings"
    }

    out_parts = []
    for part in parts:
        m = re.match(r"\s*([\d.]+)\s*(.*)", part)
        if not m:
            out_parts.append(part)
            continue

        num  = Decimal(m.group(1))
        unit = m.group(2).strip()

        unit_first_word = unit.split()[0].lower()

        if unit_first_word in whole_units:
            new_num = int(num.to_integral_value(rounding=ROUND_HALF_UP)) or 1
        else:
            new_num = (num * 2).to_integral_value(rounding=ROUND_HALF_UP) / 2
            new_num = int(new_num) if new_num == int(new_num) else float(new_num)

        out_parts.append(f"{new_num} {unit}")

    return " + ".join(out_parts)


def normalize_meal_name(name: str) -> str:
    """snack1 / snack2 → Snack"""
    return "Snack" if name.lower() in {"snack1", "snack2"} else name


def normalize_and_deduplicate_meal_keys(keys):
    seen, out = set(), []
    for k in keys:
        n = normalize_meal_name(k)
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def parse_meal_data(meal):
    """
    Returns
      text , kcal , protein , carbs , fats
    Text is formatted with quantities (e.g. “Paneer Paratha (320 g)”).
    """
    if isinstance(meal, str):
        return meal, 0, 0, 0, 0

    if isinstance(meal, dict):
        # ── single-dish form ------------------------------------------------
        if {"name", "calories"}.issubset(meal):
            name      = meal.get("name", "")
            qty_raw   = meal.get("quantity", "")
            qty       = _pretty_qty(qty_raw) if qty_raw else ""
            calories  = float(meal.get("calories", 0))
            protein   = float(meal.get("protein", 0))
            carbs     = float(meal.get("carbs", 0))
            fats      = float(meal.get("fats", 0))
            text = f"{name} ({qty})" if qty else name
            return text, calories, protein, carbs, fats

        # ── multi-dish form -------------------------------------------------
        lines = []
        kcal = prot = carb = fat = 0
        for d in meal.values():
            name = d.get("name", "")
            qty_raw = d.get("quantity", "")
            qty  = _pretty_qty(qty_raw) if qty_raw else ""
            lines.append(f"- {name} ({qty})" if qty else f"- {name}")
            kcal += float(d.get("calories", 0))
            prot += float(d.get("protein", 0))
            carb += float(d.get("carbs", 0))
            fat  += float(d.get("fats", 0))

        lines.append("")  # blank line
        lines.append(f"Cal: {kcal:.0f} | P {prot:.0f}g | C {carb:.0f}g | F {fat:.0f}g")
        return "\n".join(lines), kcal, prot, carb, fat

    # fallback
    return str(meal), 0, 0, 0, 0


def clean_text(txt: str) -> str:
    """Remove problematic unicode for FPDF (pure-ASCII)."""
    if not isinstance(txt, str):
        txt = str(txt)

    repl = {
        "✓": "OK", "✔": "OK", "✗": "X", "•": "-", "…": "...",
        "“": '"', "”": '"', "‘": "'", "’": "'",
        "–": "-", "—": "--"
    }
    for u, a in repl.items():
        txt = txt.replace(u, a)
    return "".join(c if ord(c) < 128 else "?" for c in txt)


# ── PDF generators ─────────────────────────────────────────────────────────
def create_pdf(plan: dict, filename: str):
    """
    Landscape summary table – one row per day.
    """
    pdf = FPDF("L", "mm", "A4")
    pdf.set_auto_page_break(True, 15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Personalized 7-Day Diet Plan", ln=True, align="C")
    pdf.ln(5)

    # Determine columns in JSON order
    raw_keys = []
    for d in plan["7DayPlan"]:
        for k in d:
            if k != "Day" and k not in raw_keys:
                raw_keys.append(k)
    meal_keys = normalize_and_deduplicate_meal_keys(raw_keys)
    headers   = ["Day"] + meal_keys

    # Column widths
    total_w       = pdf.w - pdf.l_margin - pdf.r_margin
    day_w         = 25
    meal_w        = (total_w - day_w) / (len(headers) - 1)

    # Header row
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(day_w, 10, "Day", border=1, align="C")
    for h in meal_keys:
        pdf.cell(meal_w, 10, h, border=1, align="C")
    pdf.ln()

    # Body
    padding     = 2
    line_height = 4
    pdf.set_font("Helvetica", "", 8)

    daily_totals = []

    for entry in plan["7DayPlan"]:
        cells       = [entry["Day"]]
        widths      = [day_w]

        day_kcal = day_p = day_c = day_f = 0

        for key in meal_keys:
            # exact key or normalised snack key
            meal = entry.get(key) or next(
                (v for k, v in entry.items() if normalize_meal_name(k) == key),
                ""
            )
            txt, kcal, p, c, f = parse_meal_data(meal)
            cells.append(clean_text(txt))
            widths.append(meal_w)
            day_kcal += kcal
            day_p    += p
            day_c    += c
            day_f    += f

        daily_totals.append(
            dict(day=entry["Day"], kcal=day_kcal, p=day_p, c=day_c, f=day_f)
        )

        # Calculate needed height
        lines_per_cell = []
        for w, t in zip(widths, cells):
            usable = w - 2 * padding
            n_lines = 0
            for line in t.split("\n"):
                if not line:
                    n_lines += 1
                    continue
                n_lines += max(1, math.ceil(pdf.get_string_width(line) / usable))
            lines_per_cell.append(n_lines)

        row_h = max(lines_per_cell) * line_height + 2 * padding

        # New page if needed
        if pdf.get_y() + row_h > pdf.page_break_trigger:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(day_w, 10, "Day", border=1, align="C")
            for h in meal_keys:
                pdf.cell(meal_w, 10, h, border=1, align="C")
            pdf.ln()
            pdf.set_font("Helvetica", "", 8)

        # Draw row borders
        x0, y0 = pdf.l_margin, pdf.get_y()
        for w in widths:
            pdf.rect(x0, y0, w, row_h)
            x0 += w

        # Fill row text
        x = pdf.l_margin
        for w, t in zip(widths, cells):
            pdf.set_xy(x + padding, y0 + padding)
            pdf.multi_cell(w - 2 * padding, line_height, t, 0, "L")
            x += w
        pdf.set_y(y0 + row_h)

    # Daily nutritional summary
    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Daily Nutritional Summary", ln=True)
    pdf.set_font("Helvetica", "", 9)

    target = None
    try:
        target = int(plan["Summary"]["AverageCalories"].split()[0])
    except Exception:
        pass

    for d in daily_totals:
        s = (f"{d['day']}: {d['kcal']:.0f} kcal | "
             f"Protein {d['p']:.0f}g ; Carbohydrates {d['c']:.0f}g ; Fats {d['f']:.0f}g")
        if target:
            diff   = d['kcal'] - target
            status = "OK" if abs(diff) <= 100 else ("OVER" if diff > 0 else "UNDER")
            s += f" )"
        pdf.cell(0, 5, clean_text(s), ln=True)

    # Plan summary
    if "Summary" in plan:
        pdf.ln(6)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Plan Summary", ln=True)
        pdf.set_font("Helvetica", "", 9)
        s = plan["Summary"]["AverageCalories"]
        pdf.cell(0, 5, clean_text(f"Average Calories: {s}"), ln=True)
        am = plan["Summary"]["AverageMacros"]
        pdf.cell(0, 5, clean_text(
            f"Average Macros – Protein: {am['Protein']}, "
            f"Carbs: {am['Carbs']}, Fats: {am['Fats']}"), ln=True)

    pdf.output(filename)


# ---------------------------------------------------------------------------
# Optional detailed version (unchanged except for calls to clean_text/parse).
# ---------------------------------------------------------------------------
def create_detailed_pdf(plan: dict, filename: str):
    pdf = FPDF("P", "mm", "A4")
    pdf.set_auto_page_break(True, 15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Personalized 7-Day Diet Plan", ln=True, align="C")
    pdf.ln(5)

    for entry in plan["7DayPlan"]:
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 8, entry["Day"], ln=True)
        pdf.ln(2)

        day_kcal = day_p = day_c = day_f = 0
        used = set()
        for k, v in entry.items():
            if k == "Day":
                continue
            nk = normalize_meal_name(k)
            if nk in used:
                continue
            used.add(nk)
            txt, kcal, p, c, f = parse_meal_data(v)
            day_kcal += kcal
            day_p    += p
            day_c    += c
            day_f    += f

            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 6, f"{nk}:", ln=True)
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 4, clean_text(txt))
            pdf.ln(1)

        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 6, clean_text(
            f"Daily Total: {day_kcal:.0f} kcal | "
            f"P {day_p:.0f}g C {day_c:.0f}g F {day_f:.0f}g"), ln=True)
        pdf.ln(6)

        if pdf.get_y() > 260 and entry != plan["7DayPlan"][-1]:
            pdf.add_page()

    if "Summary" in plan:
        if pdf.get_y() > 200:
            pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 8, "Plan Summary", ln=True)
        pdf.set_font("Helvetica", "", 11)
        s = plan["Summary"]["AverageCalories"]
        pdf.cell(0, 6, clean_text(f"Average Calories: {s}"), ln=True)
        am = plan["Summary"]["AverageMacros"]
        pdf.cell(0, 6, clean_text(
            f"Average Macros – Protein: {am['Protein']}, "
            f"Carbs: {am['Carbs']}, Fats: {am['Fats']}"), ln=True)

    pdf.output(filename)
