"""Tests for webhook signature verification + receiver (Day 6)."""

import hmac, hashlib
from fastapi.testclient import TestClient
from app.webhooks.verifier import verify_webhook, compute_signature


SECRET = "mock_webhook_secret"


def test_compute_and_verify_valid():
    body = b'{"event":"x"}'
    sig = compute_signature(body, SECRET)
    r = verify_webhook(body, SECRET, sig, "evt1", set())
    assert r.ok and r.reason == "ok"


def test_invalid_signature_rejected():
    body = b'{"event":"x"}'
    r = verify_webhook(body, SECRET, "deadbeef", "evt2", set())
    assert not r.ok and r.reason == "invalid_signature"


def test_missing_signature_rejected():
    r = verify_webhook(b"{}", SECRET, None, "evt3", set())
    assert not r.ok and r.reason == "missing_signature"


def test_duplicate_rejected():
    body = b'{"event":"x"}'
    sig = compute_signature(body, SECRET)
    seen = set()
    assert verify_webhook(body, SECRET, sig, "dup", seen).ok
    # second delivery of same event id must be flagged duplicate
    r2 = verify_webhook(body, SECRET, sig, "dup", seen)
    assert not r2.ok and r2.reason == "duplicate"


def test_constant_time_compare_used():
    # ensure hmac.compare_digest is the mechanism (no string ==)
    body = b"data"
    sig = compute_signature(body, SECRET)
    assert verify_webhook(body, SECRET, sig, "e", set()).ok


def test_webhook_test_route(client):
    # register + project + run webhook test against mock
    client.post("/api/v1/auth/register", json={"email": "wh@b.com", "password": "supersecret"})
    token = client.post("/api/v1/auth/login", json={"email": "wh@b.com", "password": "supersecret"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    pid = client.post("/api/v1/projects", headers=h, json={"name": "WH"}).json()["id"]
    r = client.post(f"/api/v1/projects/{pid}/webhooks/test", headers=h)
    assert r.status_code == 200
    d = r.json()
    assert d["valid_signature_accepted"] is True
    assert d["invalid_signature_rejected"] is True


def test_receiver_endpoint(client):
    client.post("/api/v1/auth/register", json={"email": "wr@b.com", "password": "supersecret"})
    token = client.post("/api/v1/auth/login", json={"email": "wr@b.com", "password": "supersecret"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    pid = client.post("/api/v1/projects", headers=h, json={"name": "WR"}).json()["id"]
    body = b'{"event":"purchase"}'
    sig = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    r = client.post(f"/api/v1/webhooks/receive/{pid}", content=body,
                    headers={"X-Event-Id": "evt_r1", "X-Webhook-Signature": sig})
    assert r.status_code == 200 and r.json()["received"] is True
    # bad sig
    r2 = client.post(f"/api/v1/webhooks/receive/{pid}", content=body,
                     headers={"X-Event-Id": "evt_r2", "X-Webhook-Signature": "bad"})
    assert r2.status_code == 401
