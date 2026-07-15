"""Tests for diagnosis + fixes + verification (Day 10-13).

LLM calls are mocked (monkeypatch complete_json) so tests are fast and
deterministic. The verification engine is tested for real against the mock.
"""

import pytest
from unittest.mock import patch


@pytest.fixture
def proj_client(client):
    client.post("/api/v1/auth/register", json={"email": "ai@b.com", "password": "supersecret"})
    token = client.post("/api/v1/auth/login", json={"email": "ai@b.com", "password": "supersecret"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    pid = client.post("/api/v1/projects", headers=h, json={"name": "AI"}).json()["id"]
    client.post("/api/v1/docs/seed", headers=h)
    return client, h, pid


def test_diagnose_and_verify_flow(proj_client, monkeypatch):
    client, h, pid = proj_client

    # run a failing test
    run = client.post(f"/api/v1/projects/{pid}/tests/run", headers=h,
                      json={"test_name": "Create order with missing sku"}).json()
    rid = run["test_run_id"]

    # mock the LLM diagnosis
    async def fake_diag(sys, user, cfg=None):
        return {
            "problem": "missing sku",
            "root_cause": "request body missing required 'sku' field",
            "evidence": ["Status: 400", "missing_field"],
            "confidence": 1.0,
        }
    monkeypatch.setattr("app.ai.diagnosis.complete_json", fake_diag)
    diag = client.post(f"/api/v1/projects/{pid}/test-runs/{rid}/diagnose", headers=h).json()
    assert diag["root_cause"] == "request body missing required 'sku' field"
    did = diag["diagnosis_id"]

    # mock the fixes
    async def fake_fixes(sys, user, cfg=None):
        return [{
            "fix_type": "code",
            "description": "add sku to body",
            "code": "payload['sku']='x'",
            "verification_test": "Create order with valid token",
        }]
    monkeypatch.setattr("app.ai.fixes.complete_json", fake_fixes)
    fixes = client.post(f"/api/v1/projects/{pid}/diagnoses/{did}/fixes", headers=h).json()
    assert len(fixes) == 1
    fid = fixes[0]["id"]

    # verify — reruns "Create order with valid token" which passes -> verified
    vr = client.post(f"/api/v1/projects/{pid}/fixes/{fid}/verify", headers=h).json()
    assert vr["status"] == "verified"
    assert vr["rerun_response_status"] == 200


def test_diagnosis_llm_failure_is_safe(proj_client, monkeypatch):
    client, h, pid = proj_client
    run = client.post(f"/api/v1/projects/{pid}/tests/run", headers=h,
                      json={"test_name": "Create order with missing sku"}).json()
    rid = run["test_run_id"]
    monkeypatch.setattr("app.ai.diagnosis.complete_json",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("llm down")))
    diag = client.post(f"/api/v1/projects/{pid}/test-runs/{rid}/diagnose", headers=h).json()
    assert diag["root_cause"].startswith("diagnosis_error")
    assert diag["confidence"] == 0.0
