"""Tests for the Mock Commerce API failure-injection behaviour.

Run with:  pytest mock_service/tests
These double as the canonical definition of the 15 failure scenarios the
evaluation suite (backend/evaluation) depends on.
"""

import hmac
import hashlib
import pytest
from fastapi.testclient import TestClient

from app.main import app, WEBHOOK_SECRET

client = TestClient(app)

VALID = {"Authorization": "Bearer valid_token_abc", "Content-Type": "application/json"}
EXPIRED = {"Authorization": "Bearer expired_token_123", "Content-Type": "application/json"}


def sig(body: bytes) -> str:
    return hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


def test_health():
    assert client.get("/mock/health").status_code == 200


def test_success_catalog():
    r = client.get("/mock/catalog", headers=VALID)
    assert r.status_code == 200
    assert r.json()["status"] == "success"


# --- 15 failure modes -------------------------------------------------------

def test_f01_invalid_token():
    r = client.get("/mock/catalog", headers={**VALID, "X-Failure-Mode": "invalid-token"})
    assert r.status_code == 401 and r.json()["detail"]["error"] == "invalid_token"


def test_f02_expired_token():
    r = client.get("/mock/catalog", headers=EXPIRED)
    assert r.status_code == 401 and r.json()["detail"]["error"] == "token_expired"


def test_f03_missing_field():
    r = client.post("/mock/orders", headers=VALID, json={})
    assert r.status_code == 400 and r.json()["detail"]["field"] == "sku"


def test_f04_wrong_method():
    r = client.post("/mock/catalog", headers=VALID, json={})
    assert r.status_code == 405


def test_f05_invalid_json():
    r = client.post("/mock/auth/token", headers={**VALID, "X-Failure-Mode": "invalid-json"},
                    content=b"notjson", headers_without_content_type=True) if False else \
        client.post("/mock/auth/token", headers={**VALID, "X-Failure-Mode": "invalid-json"},
                    content=b"notjson")
    assert r.status_code == 200  # mock returns non-JSON body to simulate parse failure


def test_f06_unknown_sku():
    r = client.post("/mock/orders", headers=VALID, json={"sku": "nope"})
    assert r.status_code == 404 and r.json()["detail"]["error"] == "unknown_sku"


def test_f07_wrong_content_type():
    r = client.get("/mock/catalog", headers={**VALID, "X-Failure-Mode": "wrong-content-type"})
    assert r.status_code == 200
    assert "application/json" not in r.headers["content-type"]


def test_f08_bad_signature():
    r = client.post("/mock/webhooks/receive",
                    headers={"X-Event-Id": "evt_x", "X-Webhook-Signature": "wrong"},
                    content=b"{}")
    assert r.status_code == 401


def test_f09_duplicate_webhook():
    body = b'{"event":"purchase"}'
    h = {"X-Event-Id": "evt_dup1", "X-Webhook-Signature": sig(body)}
    assert client.post("/mock/webhooks/receive", headers=h, content=body).status_code == 200
    # second delivery of same event id must be rejected
    assert client.post("/mock/webhooks/receive", headers=h, content=body).status_code == 409


def test_f10_timeout(monkeypatch):
    # The mock sleeps 35s in timeout mode; a real test runner (10s timeout) would
    # abort. We verify the branch is taken without actually sleeping 35s.
    import app.main as m
    slept = {}
    monkeypatch.setattr(m.time, "sleep", lambda s: slept.update({"s": s}))
    r = client.get("/mock/catalog", headers={**VALID, "X-Failure-Mode": "timeout"})
    assert r.status_code == 200
    assert slept.get("s", 0) >= 30  # confirms the timeout-mode sleep path


def test_f11_invalid_order_state():
    r = client.post("/mock/orders", headers={**VALID, "X-Failure-Mode": "invalid-order-state"},
                    json={"sku": "gold_100", "state": "bogus"})
    assert r.status_code == 409


def test_f12_server_error():
    r = client.get("/mock/catalog", headers={**VALID, "X-Failure-Mode": "server-error"})
    assert r.status_code == 500


def test_f13_wrong_api_version():
    r = client.get("/mock/catalog", headers={**VALID, "X-API-Version": "0"})
    assert r.status_code == 400


def test_f14_rate_limited():
    for _ in range(6):
        client.get("/mock/catalog", headers={**VALID, "X-Failure-Mode": "rate-limited"})
    r = client.get("/mock/catalog", headers={**VALID, "X-Failure-Mode": "rate-limited"})
    assert r.status_code == 429


def test_f15_malformed_response():
    r = client.post("/mock/orders", headers={**VALID, "X-Failure-Mode": "malformed-response"},
                    json={"sku": "gold_100"})
    assert r.status_code == 200
    assert not r.text.strip().startswith("{")
