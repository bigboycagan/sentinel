"""API-level tests against the live uvicorn process (see conftest.py)."""

CLEAN = '"""Clean."""\n\n\ndef add(a: int, b: int) -> int:\n    """Sum."""\n    return a + b\n'
VULNERABLE = 'def login(user, password):\n    password = "hunter2xyz"\n    return eval(user)\n'


def test_analyze_returns_report(client):
    res = client.post("/analyze", json={"code": VULNERABLE, "file_name": "v.py"})
    assert res.status_code == 200
    body = res.json()
    assert body["file_name"] == "v.py"
    assert body["language"] == "python"
    assert 0 <= body["overall_score"] <= 100
    assert body["counts"]["total"] >= 2
    assert {f["rule_id"] for f in body["findings"]} >= {"SEC001", "SEC002"}
    assert body["scores"]["security"] < 100


def test_analyze_clean_code_scores_100(client):
    res = client.post("/analyze", json={"code": CLEAN, "file_name": "clean.py"})
    assert res.status_code == 200
    assert res.json()["overall_score"] == 100


def test_analyze_empty_code_rejected(client):
    res = client.post("/analyze", json={"code": "   ", "file_name": "e.py"})
    assert res.status_code == 400
    assert res.json()["detail"] == "Please provide source code to analyze."


def test_analyze_invalid_python_reports_parse_error(client):
    res = client.post("/analyze", json={"code": "def broken(:\n  pass", "file_name": "b.py"})
    assert res.status_code == 200
    body = res.json()
    assert body["parse_error"] is not None
    assert body["scores"] is None


def test_analyze_unsupported_language_rejected(client):
    res = client.post("/analyze", json={"code": "int main(){}", "language": "c"})
    assert res.status_code == 400


def test_analyze_missing_code_is_422(client):
    assert client.post("/analyze", json={"file_name": "x.py"}).status_code == 422


def test_upload_rejects_non_python(client):
    res = client.post("/analyze/upload", files={"file": ("notes.txt", b"print(1)", "text/plain")})
    assert res.status_code == 400
    assert "Python" in res.json()["detail"]


def test_upload_analyzes_python_file(client):
    res = client.post("/analyze/upload", files={"file": ("v.py", VULNERABLE.encode(), "text/x-python")})
    assert res.status_code == 200
    assert res.json()["counts"]["total"] >= 2


def test_rules_catalog(client):
    res = client.get("/rules")
    assert res.status_code == 200
    rules = res.json()
    assert len(rules) >= 15
    sample = rules[0]
    assert {"rule_id", "title", "category", "severity", "description"} <= set(sample)


def test_settings_roundtrip(client):
    original = client.get("/settings").json()
    assert "max_file_size_bytes" in original
    res = client.put("/settings", json={"max_file_size_bytes": 500_000})
    assert res.status_code == 200
    assert res.json()["max_file_size_bytes"] == 500_000
    # restore
    client.put("/settings", json={"max_file_size_bytes": original["max_file_size_bytes"]})


def test_settings_rejects_unknown_rule(client):
    assert client.put("/settings", json={"disabled_rules": ["NOPE999"]}).status_code == 400


def test_history_lifecycle(client):
    created = client.post("/history", json={"code": VULNERABLE, "file_name": "hist.py"})
    assert created.status_code == 200
    summary = created.json()
    assert summary["file_name"] == "hist.py"
    assert summary["total_issues"] >= 2

    listed = client.get("/history").json()
    assert any(item["id"] == summary["id"] for item in listed)

    detail = client.get(f"/history/{summary['id']}")
    assert detail.status_code == 200
    assert detail.json()["id"] == summary["id"]

    assert client.delete(f"/history/{summary['id']}").status_code == 200
    assert client.get(f"/history/{summary['id']}").status_code == 404


def test_history_unknown_id_is_404(client):
    assert client.get("/history/does-not-exist").status_code == 404
