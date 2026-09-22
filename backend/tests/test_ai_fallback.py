"""With no ANTHROPIC_API_KEY, the AI layer must degrade to the rule engine / pattern matcher."""
import io
from types import SimpleNamespace

from app.services.ai import ai_available, recommend_analyses
from app.services.ai.converse import answer_query
from app.services.quality_engine import run_quality_report


def test_ai_not_available_in_tests():
    assert ai_available() is False


def test_recommend_analyses_falls_back_to_rules(sample_df):
    project = SimpleNamespace(
        title="t", research_aim="a",
        objectives=["Compare systolic bp between active and inactive students"],
        research_questions=[],
    )
    recs = recommend_analyses(project, run_quality_report(sample_df))
    assert recs
    assert all(r["source"] == "rules" for r in recs)
    assert any(r["method_key"] == "independent_ttest" for r in recs)


def test_answer_query_pattern_compare(sample_df):
    project = SimpleNamespace(title="t", research_aim="a", objectives=[])
    out = answer_query(project, sample_df, [], "compare systolic_bp between activity_level")
    assert out["source"] == "pattern"
    assert len(out["analyses"]) == 1
    assert out["analyses"][0]["method"] == "independent_ttest"
    assert out["analyses"][0]["outcome"]["status"] == "complete"


def test_answer_query_pattern_correlation(sample_df):
    project = SimpleNamespace(title="t", research_aim="a", objectives=[])
    out = answer_query(project, sample_df, [], "correlation between systolic_bp and bmi")
    assert out["analyses"][0]["method"] == "pearson"


def test_answer_query_pattern_unmatched_is_helpful(sample_df):
    project = SimpleNamespace(title="t", research_aim="a", objectives=[])
    out = answer_query(project, sample_df, [], "what should I have for lunch")
    assert out["analyses"] == []
    assert "API key" in out["reply"]


# ── endpoint-level ─────────────────────────────────────────────────────────

def _project_with_data(client, sample_df):
    pid = client.post("/api/projects", json={
        "title": "Activity & BP", "research_aim": "Relationship of activity and BP.",
        "objectives": ["Compare systolic bp between active and inactive participants",
                       "Determine whether systolic bp is associated with bmi"],
        "research_questions": [], "hypotheses": [],
    }).json()["id"]
    buf = io.BytesIO()
    sample_df.to_csv(buf, index=False)
    buf.seek(0)
    did = client.post(f"/api/projects/{pid}/datasets",
                      files={"file": ("d.csv", buf, "text/csv")}).json()["id"]
    return pid, did


def test_health_reports_ai_unavailable(client):
    body = client.get("/api/health").json()
    assert body == {"status": "ok", "ai_available": False}


def test_recommendations_endpoint_rules(client, sample_df):
    pid, _ = _project_with_data(client, sample_df)
    r = client.post(f"/api/projects/{pid}/recommendations")
    assert r.status_code == 200
    recs = r.json()
    assert recs and all(x["source"] == "rules" for x in recs)
    methods = {x["method_key"] for x in recs}
    assert "independent_ttest" in methods
    assert "pearson" in methods


def test_chat_endpoint_pattern_path_persists_analysis(client, sample_df):
    pid, did = _project_with_data(client, sample_df)
    r = client.post(f"/api/projects/{pid}/chat",
                    json={"dataset_id": did, "message": "compare systolic_bp between activity_level"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] == "pattern"
    assert len(body["analysis_ids"]) == 1
    assert body["assistant"]["role"] == "assistant"
    # the analysis is retrievable
    aid = body["analysis_ids"][0]
    assert client.get(f"/api/analyses/{aid}").json()["method"] == "independent_ttest"
    # history now has 2 messages
    assert len(client.get(f"/api/projects/{pid}/chat").json()) == 2


def test_interpret_endpoint_returns_text_without_key(client, sample_df):
    pid, did = _project_with_data(client, sample_df)
    aid = client.post(f"/api/projects/{pid}/analyses", json={
        "dataset_id": did, "method": "independent_ttest",
        "variables": {"outcome": "systolic_bp", "group": "activity_level"},
    }).json()["id"]
    r = client.post(f"/api/analyses/{aid}/interpret")
    assert r.status_code == 200
    assert r.json()["interpretation"]
