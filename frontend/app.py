# ─── frontend/app.py ──────────────────────────────────────────────────────
import os, sys, re, time, tempfile
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile

# allow backend imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import pandas as pd
from flask import Flask, request, redirect, url_for, render_template_string, flash, send_file

from ai_engine.batch_runner import row_to_user        # no COLUMN_MAP needed
from ai_engine.planner      import generate_plan
from ai_engine.pdf_generator import create_pdf

# ── CONFIG ────────────────────────────────────────────────────────────────
MAX_CALLS_PER_MIN = 3
SAFETY_DELAY      = 60 / MAX_CALLS_PER_MIN + 2
OUT_ROOT          = Path("web_generated_plans")
UPLOAD_FOLDER     = Path(tempfile.gettempdir()) / "diet_uploads"

# ── Flask setup ───────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "diet-plan-secret"

STYLE = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
<style> body{padding:2rem} </style>
"""

UPLOAD_TPL = STYLE + """
<h2>Upload Employee CSV</h2>
<form class="mt-3" method="post" action="{{url_for('upload')}}" enctype="multipart/form-data">
  <input class="form-control mb-3" type="file" name="csv" accept=".csv" required>
  <button class="btn btn-primary">Upload</button>
</form>
{% with msgs = get_flashed_messages() %}
  {% if msgs %}<div class="alert alert-danger mt-3">{{msgs[0]}}</div>{% endif %}
{% endwith %}
"""

SELECT_TPL = STYLE + """
<h2>Select Employees ({{df|length}} found)</h2>
<form method="post" action="{{url_for('generate')}}">
  <input type="hidden" name="csv_path" value="{{csv_path}}">
  <div class="form-check mb-2">
    <input class="form-check-input" type="checkbox" value="ALL" id="allBox"
           onclick="document.querySelectorAll('.emp').forEach(c=>c.checked=this.checked)">
    <label class="form-check-label" for="allBox"><strong>Select&nbsp;All</strong></label>
  </div><hr>
  {% for idx,row in df.iterrows() %}
    <div class="form-check">
      <input class="form-check-input emp" type="checkbox" name="rows"
             value="{{idx}}" id="emp{{idx}}">
      <label class="form-check-label" for="emp{{idx}}">
        {{row['Name of the employee']}} – {{row['Official Email address']}}
      </label>
    </div>
  {% endfor %}
  <button class="btn btn-success mt-3">Generate Plans</button>
</form>
"""

RESULT_TPL = STYLE + """
<h2>Generation Results</h2>
<table class="table table-bordered">
  <thead class="table-light"><tr><th>Name</th><th>Status</th><th>Time&nbsp;(s)</th></tr></thead>
  <tbody>
    {% for n,s,t in results %}
      <tr><td>{{n}}</td><td>{{s}}</td><td class="text-end">{{'%0.1f'|format(t)}}</td></tr>
    {% endfor %}
  </tbody>
</table>
{% if zip_ready %}
  <a class="btn btn-primary" href="{{url_for('download',zip_name=zip_name)}}">Download all PDFs&nbsp;(Zip)</a>
{% endif %}
"""

# ── ROUTES ────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    return render_template_string(UPLOAD_TPL)


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("csv")
    if not file or not file.filename.lower().endswith(".csv"):
        flash("Please upload a valid .csv file"); return redirect(url_for("index"))

    UPLOAD_FOLDER.mkdir(exist_ok=True)
    save_path = UPLOAD_FOLDER / f"upload_{datetime.now():%Y%m%d_%H%M%S}.csv"
    file.save(save_path)

    df = pd.read_csv(save_path)
    if df.empty:
        flash("CSV appears to have no rows"); return redirect(url_for("index"))

    return render_template_string(SELECT_TPL, df=df, csv_path=str(save_path))


@app.route("/generate", methods=["POST"])
def generate():
    csv_path = Path(request.form["csv_path"])
    selected = request.form.getlist("rows")

    df_all = pd.read_csv(csv_path)
    df = df_all if ("ALL" in selected or not selected) else df_all.loc[[int(i) for i in selected]]

    out_dir = OUT_ROOT / csv_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    results, last_call = [], 0.0
    for idx, row in df.iterrows():
        payload   = row_to_user(row)
        name_raw  = payload.get("Name of the employee", f"user_{idx}")
        safe_name = re.sub(r"[^A-Za-z0-9_\\-]+", "_", name_raw) or f"user_{idx}"
        pdf_path  = out_dir / f"{safe_name}.pdf"

        wait = SAFETY_DELAY - (time.time() - last_call)
        if wait > 0: time.sleep(wait)

        t0, status = time.time(), "OK"
        try:
            plan = generate_plan(payload)
            if plan is None: raise RuntimeError("No plan")
            create_pdf(plan, str(pdf_path))
        except Exception as e:
            status = f"FAILED ({e})"
        results.append((name_raw, status, time.time() - t0))
        last_call = time.time()

    zip_path = OUT_ROOT / f"{out_dir.name}.zip"
    with ZipFile(zip_path, "w") as zf:
        for pdf in out_dir.glob("*.pdf"): zf.write(pdf, pdf.name)

    return render_template_string(RESULT_TPL, results=results,
                                  zip_ready=True, zip_name=zip_path.name)


@app.route("/download/<zip_name>")
def download(zip_name):
    return send_file(OUT_ROOT / zip_name, as_attachment=True)


# ── RUN ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    OUT_ROOT.mkdir(exist_ok=True)
    app.run(debug=True)
