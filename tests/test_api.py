"""
Test suite for FastAPI endpoints.
Tests /api/health, /api/coverage, /api/fixtures, /api/evaluate, /api/results, and HTML report rendering.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.api.main import app
from tests.test_fixtures import make_clean_company_input

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_get_field_coverage():
    response = client.get("/api/coverage")
    assert response.status_code == 200
    data = response.json()
    assert "matrix" in data
    assert "audit_opinion" in data["matrix"]


def test_get_fixtures():
    response = client.get("/api/fixtures")
    assert response.status_code == 200
    fixtures = response.json()["fixtures"]
    assert len(fixtures) >= 5


def test_evaluate_and_html_render():
    inp = make_clean_company_input()
    payload = inp.model_dump()

    # 1. Post evaluation
    eval_resp = client.post("/api/evaluate", json=payload)
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["result"]["verdict"] == "CLEARED_TO_PHASE_2"
    assert eval_data["investor_report"]["badge_color"] == "success"
    result_id = eval_data["result"]["result_id"]

    # 2. Get result by id
    get_resp = client.get(f"/api/results/{result_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["result"]["ticker"] == "TATAMOTORS"

    # 3. Get latest by ticker
    latest_resp = client.get("/api/tickers/TATAMOTORS/latest")
    assert latest_resp.status_code == 200

    # 4. Get HTML report
    html_resp = client.get(f"/api/reports/{result_id}/html")
    assert html_resp.status_code == 200
    assert "TATAMOTORS" in html_resp.text
    # Verify mandatory SEBI disclaimer is rendered verbatim
    assert "Please consult a SEBI-registered investment adviser" in html_resp.text


def test_evaluate_versioning():
    inp = make_clean_company_input()
    inp.net_worth = None
    resp1 = client.post("/api/evaluate", json=inp.model_dump())
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["result"]["verdict"] == "HOLD_INCONCLUSIVE"
    assert data1["result"]["revision"] == 1
    res1_id = data1["result"]["result_id"]

    # Re-run supplying net worth
    inp.net_worth = 1000.0
    payload2 = inp.model_dump()
    payload2["prior_result_id"] = res1_id

    resp2 = client.post("/api/evaluate", json=payload2)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["result"]["verdict"] == "CLEARED_TO_PHASE_2"
    assert data2["result"]["revision"] == 2
    assert data2["result"]["supersedes"] == res1_id
