# AI-Powered Research Data Analysis Agent

Helps researchers move from research objectives + raw datasets to statistically
appropriate analyses, visualizations, interpretations, and reports.

Status: **end-to-end MVP working** — the full workflow from research objectives to a
downloadable report is implemented.

| Stage | What works |
|---|---|
| Research onboarding | Project + aim/objectives/questions/hypotheses CRUD |
| Dataset upload | CSV/XLSX, multi-sheet selection, versioning |
| Profiling & data quality | Deterministic profile + 5-part quality score |
| **Objective → analysis recommendations** | AI (Anthropic tool-use) with a **rule-based fallback** when no API key is set |
| **Statistics engine** | 11 methods (`app/services/stats/`), each reporting frequentist **and** Bayesian side by side, plus assumption checks |
| **Natural-language chat** | AI tool-use loop; pattern-matcher fallback ("compare X between Y") without a key |
| **Interpretation** | Deterministic plain-language template, optional AI polish |
| **Visualization** | Server-rendered matplotlib PNGs, one default chart per analysis + alternates |
| **Report generation** | Structured HTML + DOCX (project, data quality, methods, results, charts, limitations, recommendations); PDF deferred |

Everything degrades gracefully with no `ANTHROPIC_API_KEY`: recommendations fall back
to `app/services/stats/selection.py`, chat to a phrase matcher, interpretation to the
deterministic template. `GET /api/health` reports `ai_available`.

## Stack

- **Backend**: FastAPI + SQLAlchemy + SQLite (`backend/`). Stats: pandas / SciPy /
  statsmodels / pingouin. Charts: matplotlib. Reports: Jinja2 (HTML) + python-docx.
- **Frontend**: React + TypeScript + Vite + Tailwind (`frontend/`)
- **AI**: Anthropic Claude API, called only from the backend (`app/services/ai/`) via a
  tool-use architecture — the LLM reasons and calls the deterministic stats engine for
  every calculation. It is never wired to compute a statistic itself.

## Layout (added since Phase 1)

```
backend/app/
  services/stats/        registry.py, execution.py, assumptions.py, selection.py, methods/
  services/ai/           client.py, tools.py, recommend.py, converse.py, interpret.py
  services/viz/          charts.py
  services/report/       builder.py, render_html.py, render_docx.py
  services/interpretation.py
  models/                + analysis, chart, chat, report
  routers/               + analyses, charts, chat, reports
sample-data/             students_activity_bp.csv  (synthetic, for manual testing)
```

## Statistical approach: frequentist + Bayesian side by side

Per lecturer guidance, the stats engine reports both paradigms for the same analysis
rather than picking one. It uses `pingouin` rather than PyMC for the MVP — it returns
frequentist stats (t/F, p-value, CI, effect size) and a Bayes Factor (BF10) from the
*same function call* for the tests it supports, so there's no separate Bayesian code
path to maintain for those. Coverage:

| Method | Frequentist | Bayesian (pingouin) |
|---|---|---|
| Independent/paired t-test | ✅ | ✅ `pg.ttest` returns BF10 alongside p-value |
| Pearson correlation | ✅ | ✅ `pg.corr` returns BF10 alongside p-value |
| ANOVA | ✅ `pg.anova` | ❌ not supported by pingouin |
| Chi-square | ✅ | ❌ not supported by pingouin |
| Mann–Whitney U / Kruskal–Wallis | ✅ | ❌ not supported by pingouin |
| Linear / logistic regression | ✅ `statsmodels` | ❌ not supported by pingouin |

Where pingouin has no Bayes factor (ANOVA, chi-square, non-parametric tests,
regression) the result carries `bayesian.available = False` and an explicit
`bayesian.note`, so the UI and report say so plainly instead of quietly showing a
frequentist-only answer. Full posterior/credible-interval Bayesian regression and
ANOVA would need PyMC — a deliberately deferred upgrade.

Interpretation for both paradigms stays distinct: `interpretation.py` keeps the
p-value sentence and the Bayes-factor sentence separate and never calls a Bayes
factor "significant" or a p-value a posterior probability.

## Running it

**Quick (one server, one URL)** — from this folder:

```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1      # first time only
powershell -ExecutionPolicy Bypass -File run-local.ps1  # then open http://localhost:8000
```

`run-local.ps1` builds the frontend and serves the whole app (website + API) from
a single FastAPI process — the same mode used for hosting.

**Share a link with someone** — see [`SHARING.md`](SHARING.md). `share.ps1` gives a
temporary public link with no accounts; `Dockerfile` covers permanent hosting
(Hugging Face Spaces / Render / Railway / Fly.io).

**Dev mode (hot reload, two terminals)**:

```bash
cd backend && .venv\Scripts\activate && uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend && npm run dev
```

Dev frontend: http://localhost:5173 (proxies `/api/*` to :8000).
Backend docs: http://127.0.0.1:8000/docs. When `frontend/dist` exists the backend
also serves the built SPA at `/`; in dev you just ignore that and use Vite.

First-time setup:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

```bash
cd frontend
npm install
```

The app runs fully without an `ANTHROPIC_API_KEY` (rule-based recommendations,
phrase-matched chat, template interpretation). Set the key in `backend/.env` to
enable the AI recommendation engine, the natural-language chat tool-use loop, and
AI-polished interpretations. Model is `claude-opus-5` by default (`ANTHROPIC_MODEL`).

Backend tests: `cd backend && .venv\Scripts\activate && pytest -q` (82 tests).
Manual walkthrough: create a project with the 3 objectives from
`sample-data/students_activity_bp.csv`'s domain, upload that CSV, get
recommendations, run the t-test, then generate an HTML/DOCX report.

## Notes

- This project previously lived under `Downloads\Dr. Danquah`. It was moved here
  because Vite's dev server cannot run under a path containing `#`, which the
  original path had (from the Windows username). Keep it under a `#`-free path.
- SQLite DB (`backend/app.db`) and uploaded files (`backend/uploads/`) are gitignored
  and local-only — there is no seed data.
