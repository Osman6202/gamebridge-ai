"""Webhook signature verification (spec §21.2).

- HMAC-SHA256 over the raw body with the webhook secret.
- Constant-time comparison (hmac.compare_digest) to avoid timing attacks.
- In-memory idempotency set keyed by event id (a real deploy would persist this
  per project; for MVP an in-process set is sufficient to demonstrate the control).
"""

import hmac
import hashlib
from dataclasses import dataclass


@dataclass
class WebhookResult:
    ok: bool
    reason: str  # ok | invalid_signature | duplicate | missing_signature


def compute_signature(raw_body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()


def verify_webhook(
    raw_body: bytes,
    secret: str,
    client_signature: str | None,
    event_id: str | None,
    seen_event_ids: set[str],
) -> WebhookResult:
    if not client_signature:
        return WebhookResult(False, "missing_signature")
    expected = compute_signature(raw_body, secret)
    if not hmac.compare_digest(expected, client_signature):
        return WebhookResult(False, "invalid_signature")
    if event_id and event_id in seen_event_ids:
        return WebhookResult(False, "duplicate")
    if event_id:
        seen_event_ids.add(event_id)
    return WebhookResult(True, "ok")
