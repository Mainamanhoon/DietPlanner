# ─── backend/ai_engine/batch_runner.py ────────────────────────────────────
from __future__ import annotations

import argparse
import pathlib
import re
import time
from datetime import datetime

import pandas as pd

from ai_engine.planner       import generate_plan
from ai_engine.pdf_generator import create_pdf          # or create_detailed_pdf

# ╭─ SETTINGS ────────────────────────────────────────────────────────────╮
MAX_CALLS_PER_MIN = 3                                   # OpenAI rate-limit
SAFETY_DELAY      = 60 / MAX_CALLS_PER_MIN + 2          # sec between calls
OUT_DIR           = pathlib.Path("generated_plans")     # PDFs output folder
# ╰─────────────────────────────────────────────────────────────────────────╯


# ── helpers ───────────────────────────────────────────────────────────────
SAFE_NAME = re.compile(r"[^A-Za-z0-9_\-]+")


def sanitise(name: str) -> str:
    """Turn arbitrary user names into safe filenames."""
    return SAFE_NAME.sub("_", name.strip()) or f"user_{int(time.time())}"


def int_str(val, default: int | None = None) -> str:
    """
    Convert float / int / str → clean integer string.
    Returns "" if conversion fails and default is None, else str(default).
    """
    if pd.isna(val):
        return str(default) if default is not None else ""
    try:
        return str(int(float(val)))
    except Exception:
        return str(default) if default is not None else ""


# Mapping verbose headers → concise internal names
COLUMN_MAP = {
    "Name of the employee":                                        "Name",
    "Name of the employees": "Name",   # ← plural variant

    "Official Email address":                                      "Email",
    "Current body Weight":                                         "Weight",
    "Current Height (in cm)":                                      "Height",
    "Current body Height":                                         "Height",
    "Are there any preferred day you don't eat non-vegetarian food":
        "Non-Veg Days",
    "Any regional preference ( state wise)(like North Indian or south indian)":
        "Culture preference",
    "Any food allergies (Gluten intolerance / Lactose Intolerance or any other)":
        "Any food allergies",
    "Goals" : "Goals",
}

LIST_KEYS = {"Non-Veg Days", "Health Conditions"}
LIST_SEP  = re.compile(r"[;,/]\s*")


def row_to_user(row: pd.Series) -> dict:
    """Convert one survey row → payload dict for generate_plan()."""
    row = row.rename(index=lambda c: COLUMN_MAP.get(c, c))

    # ---------- numeric sanitation ----------
    name = str(row.get("Name", "") or row.get("Name of the employee", "Anonymous")).strip()
    weight_val = int_str(row.get("Weight", 60), 60)
    height_val = int_str(row.get("Height", 170), 170)
    age_val    = int_str(row.get("Age", ""),   "")

    activity   = int_str(row.get("Activity level", 3), 3)
    stress     = int_str(row.get("Rate your stress level", 3), 3)
    meals_per_day = int_str(row.get("Meal frequency in a day", 3), 3)
    goals = str(row.get("Goal","General Fitness"))

    # ---------- profile ----------
    profile = {
        "Name":      name,
        "Email":     str(row.get("Email", "")).strip(),
        "Department": str(row.get("Department", "")).strip(),
        "Gender":    str(row.get("Gender", "")).strip(),
        "Age":       age_val,
        "Weight":    f"{weight_val} kg",
        "Height":    f"{height_val} cm",
        "Weight & Height": f"{weight_val} kg, {height_val} cm",
        "Activity level": activity,
        "Stress level":   stress,
        "Goals":      str(row.get("Goals", "General wellness")).strip(),
        "Diet type":  str(row.get("Diet type", "Mixed")).strip(),
        "Meal frequency in a day": meals_per_day,
        "Culture preference": str(row.get("Culture preference", "Indian")).strip(),
        "Any food allergies": str(row.get("Any food allergies", "")).strip(),
        "Non-Veg Days": str(row.get("Non-Veg Days", "")).strip(),
        "Additional notes": str(
            row.get("Any additional information you would like to share", "")
        ).strip(),
    }

    # list splitting
    for key in LIST_KEYS:
        if profile.get(key):
            profile[key] = [p.strip() for p in LIST_SEP.split(profile[key]) if p.strip()]

    cal_goal = str(row.get("Calorie goal", "1800 kcal/day")).strip()

    # ---------- return with legacy root keys for backward-compat ----------
    return {
        # old flat keys used by legacy planner/pdf paths
        "Name" : name,
        "Age":               age_val,
        "Gender":            profile["Gender"],
        "Weight & Height":   profile["Weight & Height"],
        "Activity level":    activity,
        "Diet type":         profile["Diet type"],
        "Meal frequency in a day": meals_per_day,
        "Goals": goals,

        # modern structure
        "user_profile": profile,
        "calorie_goal": cal_goal
    }


# ── CLI progress menu (optional) ──────────────────────────────────────────
def display_menu(df: pd.DataFrame):
    print("\nAvailable users\n────────────────")
    for idx, row in df.iterrows():
        print(f"[{idx:>3}] {row.get('Name', '(unnamed)')}")
    print("\nChoose indices (e.g. 0 4 7),  'all', or ENTER to abort.\n")


# ── main batch loop ───────────────────────────────────────────────────────
def main(csv_path: pathlib.Path, rows: list[int] | None, force_all: bool):
    OUT_DIR.mkdir(exist_ok=True)
    df = pd.read_csv(csv_path)
    df = df.rename(columns=COLUMN_MAP)     # ← ensure ‘Name’ etc. exist

    # filter “yes” on personalised-plan column if present
    yes_col = "Would you be interested in a personalized diet plan"
    if yes_col in df.columns:
        df = df[df[yes_col].fillna("").str.strip().str.lower() == "yes"]

    # interactive row selection when run via CLI
    if not force_all and rows is None:
        display_menu(df)
        choice = input("Your choice: ").strip()
        if not choice:
            print("Aborted.")
            return
        rows = list(df.index) if choice.lower() == "all" else \
               [int(x) for x in choice.split() if x.isdigit()]

    rows = list(df.index) if force_all else rows or []
    if not rows:
        print("Nothing selected.")
        return

    print("\nGenerating …\n")
    last_call = 0.0
    results   = []

    for idx in rows:
        row       = df.loc[idx]
        payload   = row_to_user(row)
        name_raw  = payload["user_profile"]["Name"] or f"user_{idx}"
        pdf_file  = OUT_DIR / f"{sanitise(name_raw)}.pdf"

        # simple rate-limit guard
        wait = SAFETY_DELAY - (time.time() - last_call)
        if wait > 0:
            time.sleep(wait)

        t0     = datetime.now()
        status = "OK"
        try:
            plan = generate_plan(payload)
            if plan is None:
                raise RuntimeError("No plan returned")
            create_pdf(plan, str(pdf_file))          # or create_detailed_pdf
        except Exception as err:
            status = f"FAILED ({err})"
        elapsed = (datetime.now() - t0).total_seconds()

        print(f"{name_raw:<30} … {status:<25} {elapsed:>6.1f}s")
        results.append((name_raw, status, elapsed))
        last_call = time.time()

    # summary
    print("\nSummary\n────────")
    for n, s, t in results:
        print(f"{n:<30} {s:<25} {t:>6.1f}s")
    print(f"\nPDFs saved to → {OUT_DIR.resolve()}")


# ── CLI entrypoint ────────────────────────────────────────────────────────
if __name__ == "__main__":
    argp = argparse.ArgumentParser(description="Batch diet-plan generator")
    argp.add_argument("csv", help="CSV file with survey responses")
    argp.add_argument("--all",  action="store_true", help="process everyone")
    argp.add_argument("--rows", nargs="*", type=int,
                      help="specific row indices (0-based) to process")
    a = argp.parse_args()
    main(pathlib.Path(a.csv), a.rows, a.all)
