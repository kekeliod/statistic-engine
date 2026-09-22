"""Render a report doc to a single self-contained HTML file (base64 images)."""
from __future__ import annotations

import base64
from pathlib import Path

from jinja2 import Environment

_ENV = Environment(autoescape=True)

_TEMPLATE = _ENV.from_string(
    """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{{ doc.title }}</title>
<style>
 body{font:15px/1.6 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#1e293b;
   max-width:820px;margin:2rem auto;padding:0 1.2rem}
 h1{font-size:1.7rem;margin-bottom:.2rem}
 h2{font-size:1.25rem;margin-top:2.2rem;border-bottom:2px solid #e2e8f0;padding-bottom:.3rem}
 h3{font-size:1.05rem;margin-top:1.6rem}
 .muted{color:#64748b;font-size:.9rem}
 table{border-collapse:collapse;width:100%;margin:.6rem 0;font-size:.9rem}
 th,td{border:1px solid #e2e8f0;padding:.35rem .55rem;text-align:left}
 th{background:#f8fafc}
 .cards{display:flex;gap:1rem;flex-wrap:wrap;margin:.6rem 0}
 .card{flex:1;min-width:240px;border:1px solid #e2e8f0;border-radius:8px;padding:.8rem}
 .warn{background:#fffbeb;border-color:#fde68a}
 .ok{background:#f0fdf4;border-color:#bbf7d0}
 ul{margin:.4rem 0 .4rem 1.2rem}
 img{max-width:100%;border:1px solid #e2e8f0;border-radius:6px;margin:.5rem 0}
 code{background:#f1f5f9;padding:.05rem .3rem;border-radius:3px}
</style></head><body>

<h1>{{ doc.title }}</h1>
<p class="muted">Generated {{ doc.generated_at }}</p>

<h2>1. Project</h2>
<p><strong>Aim.</strong> {{ doc.project.aim }}</p>
{% if doc.project.objectives %}<p><strong>Objectives</strong></p><ol>
{% for o in doc.project.objectives %}<li>{{ o }}</li>{% endfor %}</ol>{% endif %}
{% if doc.project.research_questions %}<p><strong>Research questions</strong></p><ul>
{% for q in doc.project.research_questions %}<li>{{ q }}</li>{% endfor %}</ul>{% endif %}
{% if doc.project.hypotheses %}<p><strong>Hypotheses</strong></p><ul>
{% for h in doc.project.hypotheses %}<li>{{ h }}</li>{% endfor %}</ul>{% endif %}

<h2>2. Dataset</h2>
<p>{{ doc.dataset.filename }}{% if doc.dataset.sheet_name %} (sheet: {{ doc.dataset.sheet_name }}){% endif %}
 — {{ doc.dataset.n_rows }} rows × {{ doc.dataset.n_columns }} columns.</p>
<table><tr><th>Column</th><th>Type</th><th>Missing %</th><th>Unique</th></tr>
{% for c in doc.dataset.columns %}<tr><td>{{ c.name }}</td><td>{{ c.dtype }}</td>
<td>{{ c.missing_pct }}</td><td>{{ c.unique_count }}</td></tr>{% endfor %}</table>

<h2>3. Data Quality</h2>
<p>Overall score: <strong>{{ doc.data_quality.score.overall }}/100</strong>
 (completeness {{ doc.data_quality.score.completeness }},
 validity {{ doc.data_quality.score.validity }},
 consistency {{ doc.data_quality.score.consistency }},
 duplicates {{ doc.data_quality.score.duplicates }},
 outliers {{ doc.data_quality.score.outliers }}).</p>
{% if doc.data_quality.duplicate_row_count %}<p>{{ doc.data_quality.duplicate_row_count }} duplicate row(s) detected (not removed).</p>{% endif %}
{% if doc.data_quality.outlier_columns %}<p>Columns with flagged outliers: {{ doc.data_quality.outlier_columns|join(", ") }}.</p>{% endif %}

<h2>4. Statistical Methods</h2>
<ul>{% for m in doc.methods %}<li><strong>{{ m.label }}</strong> — {{ m.description }}
 {% if m.bayesian_supported %}<em>(reports a Bayes factor)</em>{% else %}<em>(frequentist only in this toolset)</em>{% endif %}</li>{% endfor %}</ul>

<h2>5. Results</h2>
{% for a in doc.analyses %}
<h3>{{ loop.index }}. {{ a.method_label }}{% if a.objective %} — {{ a.objective }}{% endif %}</h3>
{% if a.status != "complete" %}
<p class="warn">This analysis did not complete: {{ a.error }}</p>
{% else %}
<p class="muted">Variables: {% for k,v in a.variables.items() %}{{ k }} = {{ v }}{% if not loop.last %}; {% endif %}{% endfor %}
 · n = {{ a.n_used }}{% if a.n_excluded %} ({{ a.n_excluded }} excluded){% endif %}</p>
<div class="cards">
 <div class="card"><strong>Frequentist</strong><br>
  {{ a.frequentist.statistic.name }} = {{ "%.4g"|format(a.frequentist.statistic.value) if a.frequentist.statistic.value is not none else "—" }}{% if a.frequentist.df is not none %}, df = {{ a.frequentist.df }}{% endif %}<br>
  {% if a.frequentist.p_value is not none %}p = {{ "%.4f"|format(a.frequentist.p_value) }}<br>{% endif %}
  {% if a.frequentist.effect_size and a.frequentist.effect_size.value is not none %}{{ a.frequentist.effect_size.name }} = {{ "%.3g"|format(a.frequentist.effect_size.value) }}{% if a.frequentist.effect_size.magnitude %} ({{ a.frequentist.effect_size.magnitude }}){% endif %}<br>{% endif %}
  <span class="muted">{{ a.frequentist.summary }}</span></div>
 <div class="card{% if not a.bayesian.available %} muted{% endif %}"><strong>Bayesian</strong><br>
  {% if a.bayesian.available and a.bayesian.bayes_factor_10 is not none %}
   BF<sub>10</sub> = {{ "%.3g"|format(a.bayesian.bayes_factor_10) }} — {{ a.bayesian.interpretation }}<br>
   <span class="muted">A Bayes factor is not a p-value and does not denote "significance".</span>
  {% else %}<span class="muted">{{ a.bayesian.note }}</span>{% endif %}</div>
</div>
{% for t in a.tables %}
<p class="muted">{{ t.title }}</p>
<table><tr>{% for c in t.columns %}<th>{{ c }}</th>{% endfor %}</tr>
{% for row in t.rows %}<tr>{% for cell in row %}<td>{{ cell if cell is not none else "—" }}</td>{% endfor %}</tr>{% endfor %}</table>
{% endfor %}
{% if a.assumptions %}<p class="muted">Assumption checks:</p><ul>
{% for chk in a.assumptions %}<li>{{ "✓" if chk.passed else ("✗" if chk.passed == false else "?") }} {{ chk.label }} — {{ chk.detail }}{% if chk.recommendation %} <em>{{ chk.recommendation }}</em>{% endif %}</li>{% endfor %}</ul>{% endif %}
{% if a.chart_data_uri %}<img src="{{ a.chart_data_uri }}" alt="{{ a.chart.title }}">{% endif %}
{% if a.interpretation %}<p><strong>Interpretation.</strong> {{ a.interpretation }}</p>{% endif %}
{% endif %}
{% endfor %}

<h2>6. Limitations</h2>
<ul>{% for l in doc.limitations %}<li>{{ l }}</li>{% endfor %}
{% if not doc.limitations %}<li>No specific limitations flagged automatically.</li>{% endif %}</ul>

<h2>7. Recommendations</h2>
<ul>{% for r in doc.recommendations %}<li>{{ r }}</li>{% endfor %}</ul>

</body></html>"""
)


def _embed_charts(doc: dict) -> dict:
    for a in doc["analyses"]:
        chart = a.get("chart")
        a["chart_data_uri"] = None
        if chart and Path(chart["stored_path"]).exists():
            data = base64.b64encode(Path(chart["stored_path"]).read_bytes()).decode()
            a["chart_data_uri"] = f"data:image/png;base64,{data}"
    return doc


def render_html(doc: dict) -> str:
    return _TEMPLATE.render(doc=_embed_charts(dict(doc)))
