import io

from app.services.stats import run_analysis
from app.services.viz.charts import chart_for_result, render_chart


def _result(sample_df, method, variables):
    out = run_analysis(sample_df, method, variables, {})
    assert out["status"] == "complete", out.get("error")
    return out["result"]


def test_chart_for_result_picks_expected_kinds(sample_df):
    assert chart_for_result(_result(sample_df, "independent_ttest",
                                   {"outcome": "systolic_bp", "group": "activity_level"})) == "grouped_box"
    assert chart_for_result(_result(sample_df, "pearson",
                                   {"variable_1": "systolic_bp", "variable_2": "bmi"})) == "scatter_fit"
    assert chart_for_result(_result(sample_df, "chi_square",
                                   {"variable_1": "sex", "variable_2": "year_group"})) == "grouped_bar"


def test_every_default_chart_renders_a_nonempty_png(tmp_path, sample_df):
    cases = [
        ("independent_ttest", {"outcome": "systolic_bp", "group": "activity_level"}),
        ("mann_whitney", {"outcome": "systolic_bp", "group": "activity_level"}),
        ("one_way_anova", {"outcome": "bmi", "group": "year_group"}),
        ("kruskal_wallis", {"outcome": "bmi", "group": "year_group"}),
        ("paired_ttest", {"measure_1": "systolic_bp", "measure_2": "diastolic_bp"}),
        ("pearson", {"variable_1": "systolic_bp", "variable_2": "bmi"}),
        ("spearman", {"variable_1": "systolic_bp", "variable_2": "bmi"}),
        ("linear_regression", {"outcome": "systolic_bp", "predictors": ["bmi", "age"]}),
        ("logistic_regression", {"outcome": "activity_level", "predictors": ["systolic_bp", "bmi"]}),
        ("chi_square", {"variable_1": "sex", "variable_2": "year_group"}),
        ("descriptive", {"variables": ["systolic_bp", "bmi"]}),
    ]
    for method, variables in cases:
        result = _result(sample_df, method, variables)
        kind = chart_for_result(result)
        path, name, title = render_chart(kind, sample_df, result, tmp_path / "charts")
        assert path.exists() and path.stat().st_size > 500, f"{method} produced an empty PNG"
        assert name.endswith(".png")


# ── endpoint-level ────────────────────────────────────────────────────────

def test_analysis_endpoint_attaches_a_chart(client, sample_df):
    pid = client.post("/api/projects", json={
        "title": "p", "research_aim": "a", "objectives": [], "research_questions": [], "hypotheses": [],
    }).json()["id"]
    buf = io.BytesIO()
    sample_df.to_csv(buf, index=False)
    buf.seek(0)
    did = client.post(f"/api/projects/{pid}/datasets",
                      files={"file": ("d.csv", buf, "text/csv")}).json()["id"]

    body = client.post(f"/api/projects/{pid}/analyses", json={
        "dataset_id": did, "method": "independent_ttest",
        "variables": {"outcome": "systolic_bp", "group": "activity_level"},
    }).json()
    assert body["status"] == "complete"
    assert len(body["charts"]) == 1
    chart_id = body["charts"][0]["id"]

    img = client.get(f"/api/charts/{chart_id}")
    assert img.status_code == 200
    assert img.headers["content-type"] == "image/png"
    assert len(img.content) > 500

    # regenerate as an alternate kind
    alt = client.post(f"/api/analyses/{body['id']}/charts", json={"kind": "bar_means"})
    assert alt.status_code == 201
    assert alt.json()["kind"] == "bar_means"
    assert len(client.get(f"/api/analyses/{body['id']}/charts").json()) == 2
