import io

import pandas as pd


def _make_project(client):
    r = client.post("/api/projects", json={
        "title": "Physical activity and blood pressure",
        "research_aim": "Investigate the relationship between physical activity and blood pressure.",
        "objectives": [
            "Determine the average blood pressure of participants.",
            "Compare systolic bp between physically active and inactive participants.",
        ],
        "research_questions": [],
        "hypotheses": [],
    })
    assert r.status_code == 201
    return r.json()["id"]


def _upload(client, project_id, sample_df):
    buf = io.BytesIO()
    sample_df.to_csv(buf, index=False)
    buf.seek(0)
    r = client.post(
        f"/api/projects/{project_id}/datasets",
        files={"file": ("students.csv", buf, "text/csv")},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_methods_endpoint_lists_registry(client):
    r = client.get("/api/methods")
    assert r.status_code == 200
    keys = {m["key"] for m in r.json()}
    assert "independent_ttest" in keys
    ttest = next(m for m in r.json() if m["key"] == "independent_ttest")
    assert ttest["bayesian_supported"] is True
    assert {role["name"] for role in ttest["roles"]} == {"outcome", "group"}


def test_create_and_fetch_ttest_analysis(client, sample_df):
    pid = _make_project(client)
    did = _upload(client, pid, sample_df)

    r = client.post(f"/api/projects/{pid}/analyses", json={
        "dataset_id": did,
        "method": "independent_ttest",
        "variables": {"outcome": "systolic_bp", "group": "activity_level"},
        "objective_index": 1,
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "complete"
    assert body["result"]["bayesian"]["available"] is True
    assert body["result"]["frequentist"]["p_value"] is not None
    assert "t-test" in body["interpretation"].lower()
    assert "Bayes factor" in body["interpretation"] or "BF" in body["interpretation"]

    aid = body["id"]
    assert client.get(f"/api/analyses/{aid}").json()["method"] == "independent_ttest"
    assert len(client.get(f"/api/projects/{pid}/analyses").json()) == 1

    rr = client.post(f"/api/analyses/{aid}/rerun")
    assert rr.status_code == 200 and rr.json()["status"] == "complete"

    assert client.delete(f"/api/analyses/{aid}").status_code == 204
    assert client.get(f"/api/analyses/{aid}").status_code == 404


def test_failed_analysis_is_persisted_not_500(client, sample_df):
    pid = _make_project(client)
    did = _upload(client, pid, sample_df)
    r = client.post(f"/api/projects/{pid}/analyses", json={
        "dataset_id": did,
        "method": "independent_ttest",
        "variables": {"outcome": "systolic_bp", "group": "year_group"},  # 3 levels
    })
    assert r.status_code == 201
    assert r.json()["status"] == "failed"
    assert r.json()["error"]
    assert r.json()["result"] is None
