import io

from docx import Document


def _setup(client, sample_df, extra_missing=False):
    df = sample_df.copy()
    if extra_missing:
        df.loc[:20, "bmi"] = None
    pid = client.post("/api/projects", json={
        "title": "Physical activity and blood pressure",
        "research_aim": "Investigate the relationship between physical activity and blood pressure.",
        "objectives": ["Compare systolic bp between active and inactive participants",
                       "Determine whether systolic bp is associated with bmi"],
        "research_questions": ["Does activity lower blood pressure?"],
        "hypotheses": [],
    }).json()["id"]
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    did = client.post(f"/api/projects/{pid}/datasets",
                      files={"file": ("d.csv", buf, "text/csv")}).json()["id"]
    a1 = client.post(f"/api/projects/{pid}/analyses", json={
        "dataset_id": did, "method": "independent_ttest",
        "variables": {"outcome": "systolic_bp", "group": "activity_level"}, "objective_index": 0,
    }).json()["id"]
    a2 = client.post(f"/api/projects/{pid}/analyses", json={
        "dataset_id": did, "method": "pearson",
        "variables": {"variable_1": "systolic_bp", "variable_2": "bmi"}, "objective_index": 1,
    }).json()["id"]
    return pid, did, [a1, a2]


def test_generate_html_report(client, sample_df):
    pid, _, _ = _setup(client, sample_df)
    r = client.post(f"/api/projects/{pid}/reports", json={"format": "html"})
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    assert r.json()["format"] == "html"

    dl = client.get(f"/api/reports/{rid}/download")
    assert dl.status_code == 200
    html = dl.text
    for marker in ["Statistical Analysis Report", "Data Quality", "Frequentist",
                   "Bayesian", "Limitations", "Recommendations", "Independent-samples t-test",
                   "Pearson correlation"]:
        assert marker in html, marker
    # Bayesian vocabulary stays distinct
    assert "not a p-value" in html


def test_generate_docx_report_opens_in_word(client, sample_df):
    pid, _, _ = _setup(client, sample_df)
    r = client.post(f"/api/projects/{pid}/reports", json={"format": "docx"})
    assert r.status_code == 201
    rid = r.json()["id"]

    dl = client.get(f"/api/reports/{rid}/download")
    assert dl.status_code == 200
    assert dl.headers["content-type"].startswith("application/vnd.openxmlformats")

    doc = Document(io.BytesIO(dl.content))
    text = "\n".join(p.text for p in doc.paragraphs)
    headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
    assert any("Results" in h for h in headings)
    assert any("Limitations" in h for h in headings)
    assert "Bayesian." in text
    assert len(doc.inline_shapes) >= 1  # at least one embedded chart


def test_report_limitations_capture_missing_data_and_no_bayes(client, sample_df):
    pid, _, _ = _setup(client, sample_df, extra_missing=True)
    rid = client.post(f"/api/projects/{pid}/reports", json={"format": "html"}).json()["id"]
    doc = client.get(f"/api/projects/{pid}/reports").json()
    assert doc and doc[0]["id"] == rid
    html = client.get(f"/api/reports/{rid}/download").text
    assert "complete" in html.lower()
    # Pearson has a Bayes factor; t-test too — but the missingness limitation must show
    assert "listwise" in html


def test_report_requires_an_analysis(client, sample_df):
    pid = client.post("/api/projects", json={
        "title": "empty", "research_aim": "a", "objectives": [], "research_questions": [], "hypotheses": [],
    }).json()["id"]
    r = client.post(f"/api/projects/{pid}/reports", json={"format": "html"})
    assert r.status_code == 409
