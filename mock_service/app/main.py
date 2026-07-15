"""GameBridge AI — Mock Commerce API.

A controlled game-commerce simulator used by the test runner to produce
predictable success and failure cases. Failure modes are selected via the
`X-Failure-Mode` header so the evaluation suite can inject exact scenarios.

Supported failure modes (see spec §17.3):
  invalid-token, expired-token, missing-field, wrong-method, invalid-json,
  duplicate-webhook, bad-signature, timeout, wrong-content-type, invalid-sku,
  invalid-order-state, server-error, wrong-api-version, rate-limited,
  malformed-response
"""

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
import time
import json
import os

app = FastAPI(title="GameBridge Mock Commerce API", version="0.1.0")

# Catalog of fake products
CATALOG = [
    {"sku": "gold_100", "name": "100 Gold Coins", "price": 1.99, "currency": "USD"},
    {"sku": "gem_50", "name": "50 Gems", "price": 4.99, "currency": "USD"},
    {"sku": "pass_month", "name": "Monthly Pass", "price": 9.99, "currency": "USD"},
]

VALID_TOKENS = {"valid_token_abc", "test_token_xyz"}
EXPIRED_TOKENS = {"expired_token_123"}
WEBHOOK_SECRET = "mock_webhook_secret"

# In-memory idempotency / duplicate tracking
_seen_webhook_events: set[str] = set()
_request_counts: dict[str, int] = {}


def _failure_mode(headers: dict) -> str | None:
    return headers.get("x-failure-mode") or headers.get("X-Failure-Mode")


def _check_auth(headers: dict, *, allow_missing_ok: bool = False):
    """Return (token_ok, token_expired, token_value)."""
    auth = headers.get("authorization") or headers.get("Authorization")
    if not auth:
        return (allow_missing_ok, False, None)
    if not auth.startswith("Bearer "):
        return (False, False, None)
    token = auth[len("Bearer "):]
    if token in VALID_TOKENS:
        return (True, False, token)
    if token in EXPIRED_TOKENS:
        return (False, True, token)
    return (False, False, token)


def _rate_check(client: str) -> bool:
    """Very small rate limit for the rate-limited failure mode."""
    _request_counts[client] = _request_counts.get(client, 0) + 1
    return _request_counts[client] <= 5  # allow 5, then 429


@app.get("/mock/catalog")
async def get_catalog(request: Request):
    mode = _failure_mode(dict(request.headers))
    h = dict(request.headers)
    ok, expired, _ = _check_auth(h)

    # API version gate (covers wrong-api-version)
    api_ver = h.get("x-api-version")
    if api_ver is not None and api_ver not in ("1", "2024-01-01"):
        raise HTTPException(status_code=400, detail={"error": "unsupported_api_version", "version": api_ver})

    if mode == "timeout":
        time.sleep(35)  # exceed typical 10s test timeout
        return {"status": "success", "items": CATALOG}
    if mode == "rate-limited" and not _rate_check(request.client.host if request.client else "anon"):
        raise HTTPException(status_code=429, detail={"error": "rate_limited"})

    if mode == "invalid-token" or (not ok and not expired):
        raise HTTPException(status_code=401, detail={"error": "invalid_token"})
    if mode == "expired-token" or expired:
        raise HTTPException(status_code=401, detail={"error": "token_expired"})
    if mode == "wrong-content-type":
        return JSONResponse({"items": CATALOG}, media_type="text/plain")
    if mode == "server-error":
        raise HTTPException(status_code=500, detail={"error": "internal_server_error"})

    return {"status": "success", "items": CATALOG}


@app.post("/mock/auth/token")
async def issue_token(request: Request):
    mode = _failure_mode(dict(request.headers))
    if mode == "invalid-json":
        return PlainTextResponse("not json", media_type="application/json", status_code=200)
    if mode == "server-error":
        raise HTTPException(status_code=500, detail={"error": "internal_server_error"})
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})
    if mode == "missing-field" and "client_id" not in (body or {}):
        raise HTTPException(status_code=400, detail={"error": "missing_field", "field": "client_id"})
    return {"access_token": "valid_token_abc", "token_type": "Bearer", "expires_in": 3600}


@app.post("/mock/orders")
async def create_order(request: Request):
    mode = _failure_mode(dict(request.headers))
    h = dict(request.headers)
    ok, expired, _ = _check_auth(h)

    api_ver = h.get("x-api-version")
    if api_ver is not None and api_ver not in ("1", "2024-01-01"):
        raise HTTPException(status_code=400, detail={"error": "unsupported_api_version", "version": api_ver})
    if mode == "timeout":
        time.sleep(35)
        return {"status": "success", "order_id": "ord_0001"}

    if mode == "invalid-token" or (not ok):
        raise HTTPException(status_code=401, detail={"error": "invalid_token"})
    if mode == "expired-token" or expired:
        raise HTTPException(status_code=401, detail={"error": "token_expired"})

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "invalid_json"})

    if mode == "wrong-content-type":
        pass
    if mode == "missing-field" or "sku" not in body:
        raise HTTPException(status_code=400, detail={"error": "missing_field", "field": "sku"})
    if mode == "invalid-sku" or body["sku"] not in {c["sku"] for c in CATALOG}:
        raise HTTPException(status_code=404, detail={"error": "unknown_sku", "sku": body.get("sku")})
    if mode == "invalid-order-state" and body.get("state") not in (None, "new", "pending"):
        raise HTTPException(status_code=409, detail={"error": "invalid_order_state", "state": body.get("state")})
    if mode == "server-error":
        raise HTTPException(status_code=500, detail={"error": "internal_server_error"})
    if mode == "malformed-response":
        return PlainTextResponse("<not-json>", media_type="application/json")

    return {"status": "success", "order_id": "ord_0001", "sku": body.get("sku"), "state": "created"}


@app.post("/mock/webhooks/send")
async def send_webhook(request: Request):
    """Simulates delivering a webhook event to a receiver (for testing receivers)."""
    mode = _failure_mode(dict(request.headers))
    if mode == "duplicate-webhook":
        # Signal the receiver test to deliver the same event id twice.
        return {"status": "ok", "event_id": "evt_dup", "deliver_twice": True}
    return {"status": "ok", "event_id": "evt_001", "deliver_twice": False}


def _compute_signature(raw_body: bytes, secret: str) -> str:
    import hmac
    import hashlib
    return hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()


@app.post("/mock/webhooks/receive")
async def receive_webhook(request: Request):
    """A webhook receiver endpoint the test runner can POST to.

    Validates signature and rejects duplicate event ids (idempotency).
    Failure modes:
      bad-signature  -> client sends a wrong signature (receiver must reject)
      duplicate-webhook -> same event_id delivered twice (receiver must ignore 2nd)
    """
    mode = _failure_mode(dict(request.headers))
    raw = await request.body()
    event_id = request.headers.get("x-event-id", "evt_unknown")
    client_sig = request.headers.get("x-webhook-signature")

    expected_sig = _compute_signature(raw, WEBHOOK_SECRET)
    if mode == "bad-signature":
        client_sig = "deadbeef"  # force mismatch

    if client_sig != expected_sig:
        # A correct receiver rejects this; we mirror that behavior.
        return JSONResponse(
            {"received": False, "reason": "invalid_signature"}, status_code=401
        )

    if event_id in _seen_webhook_events:
        return JSONResponse(
            {"received": False, "reason": "duplicate_event", "event_id": event_id},
            status_code=409,
        )

    _seen_webhook_events.add(event_id)
    return {"received": True, "event_id": event_id, "signature_valid": True}


@app.get("/mock/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
