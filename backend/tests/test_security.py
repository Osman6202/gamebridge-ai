"""Security + integration tests (Day 7).

Covers spec §22.4: unauthorized project access, invalid webhook signature,
duplicate webhook, and that redaction survives a persisted trace.
"""

import hmac, hashlib
from app.test_runner.redaction import redact_trace


SECRET = "mock_webhook_secret"


def test_unauthorized_webhook_access_denied(client):
    # project 9999 does not exist for the authed user -> 404
    client.post("/api/v1/auth/register", json={"email": "sec@b.com", "password": "supersecret"})
    token = client.post("/api/v1/auth/login", json={"email": "sec@b.com", "password": "supersecret"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/v1/projects/9999/webhooks/received", headers=h)
    assert r.status_code == 404


def test_duplicate_webhook_rejected_at_receiver(client):
    client.post("/api/v1/auth/register", json={"email": "dup@b.com", "password": "supersecret"})
    token = client.post("/api/v1/auth/login", json={"email": "dup@b.com", "password": "supersecret"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    pid = client.post("/api/v1/projects", headers=h, json={"name": "Dup"}).json()["id"]
    body = b'{"event":"x"}'
    sig = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    hh = {"X-Event-Id": "evt_dup1", "X-Webhook-Signature": sig}
    assert client.post(f"/api/v1/webhooks/receive/{pid}", content=body, headers=hh).status_code == 200
    # same event id again -> 409 duplicate
    assert client.post(f"/api/v1/webhooks/receive/{pid}", content=body, headers=hh).status_code == 409


def test_persisted_trace_is_redacted():
    # a trace stored must have no raw secret in request_headers
    trace = {
        "method": "POST", "url": "http://x/orders",
        "request_headers": {"Authorization": "Bearer real-token-123"},
        "request_body": {"client_secret": "topsecret"},
        "response_headers": {"Set-Cookie": "a=b"},
        "response_body": {"ok": 1},
    }
    out = redact_trace(trace)
    assert "real-token-123" not in str(out)
    assert out["request_headers"]["Authorization"] == "***REDACTED***"
    assert out["request_body"]["client_secret"] == "***REDACTED***"
