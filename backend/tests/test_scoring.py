import os
from backend.app import app, score_content, CATEGORIES


def test_score_schema():
    result = score_content({"headline": "You won't believe this", "snippet": "Act now"}, "r1")
    assert "rustmeter_score" in result
    assert "aim_score" not in result
    for key in CATEGORIES:
        assert key in result["category_scores"]


def test_analyze_endpoint_and_optin_storage(tmp_path, monkeypatch):
    client = app.test_client()
    payload = {"hash": "abc", "headline": "Experts say", "snippet": "many believe", "store_training_data": False}
    resp = client.post('/analyze', json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "rustmeter_score" in data
