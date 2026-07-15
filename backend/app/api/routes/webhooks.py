"""Webhook routes (Day 6).

- POST /api/v1/projects/{id}/webhooks/test  -> fires a signed webhook at the mock
  receiver and reports whether it was accepted (and that a tampered signature is rejected).
- POST /api/v1/webhooks/receive/{project_id} -> the backend's own receiver that
  validates HMAC signatures (constant-time) and rejects duplicates.

The receiver stores received events in-memory for MVP (a deploy would persist).
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
import httpx

from app.core.database import get_db
from app.models import User, Project
from app.api.dependencies import get_current_user
from app.webhooks.verifier import verify_webhook, compute_signature
from app.core.config import settings

router = APIRouter(prefix="/api/v1", tags=["webhooks"])

# In-memory idempotency + received-event store (MVP). Keyed by project_id.
_seen_events: dict[int, set[str]] = {}
_received: dict[int, list[dict]] = {}

WEBHOOK_SECRET = "mock_webhook_secret"  # demo secret; env-overridable in real deploy


@router.post("/projects/{project_id}/webhooks/test")
async def webhook_test(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.get(Project, project_id)
    if project is None or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="project_not_found")

    import uuid
    event_body = b'{"event":"purchase","order_id":"ord_99"}'
    event_id = f"evt_test_{uuid.uuid4().hex[:8]}"
    sig = compute_signature(event_body, WEBHOOK_SECRET)

    async with httpx.AsyncClient(timeout=10) as client:
        # 1) valid signature -> mock receiver should accept (200)
        good = await client.post(
            f"{settings.mock_api_base}/mock/webhooks/receive",
            content=event_body,
            headers={"X-Event-Id": event_id, "X-Webhook-Signature": sig},
        )
        # 2) tampered signature -> mock receiver should reject (401)
        bad = await client.post(
            f"{settings.mock_api_base}/mock/webhooks/receive",
            content=event_body,
            headers={"X-Event-Id": event_id + "_bad", "X-Webhook-Signature": "deadbeef"},
        )

    return {
        "valid_signature_accepted": good.status_code == 200,
        "invalid_signature_rejected": bad.status_code == 401,
        "mock_response_valid": good.status_code,
        "mock_response_invalid": bad.status_code,
    }


@router.post("/webhooks/receive/{project_id}")
async def receive_webhook(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    # Note: a public receiver usually has no auth; project ownership is enforced
    # by the caller knowing/using the project-specific secret in a real system.
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project_not_found")

    raw = await request.body()
    event_id = request.headers.get("x-event-id")
    client_sig = request.headers.get("x-webhook-signature")

    seen = _seen_events.setdefault(project_id, set())
    result = verify_webhook(raw, WEBHOOK_SECRET, client_sig, event_id, seen)
    if not result.ok:
        code = 401 if result.reason == "invalid_signature" else 409
        raise HTTPException(status_code=code, detail={"received": False, "reason": result.reason, "event_id": event_id})

    _received.setdefault(project_id, []).append(
        {"event_id": event_id, "body": raw.decode("utf-8", "replace")}
    )
    return {"received": True, "event_id": event_id, "signature_valid": True}


@router.get("/projects/{project_id}/webhooks/received")
def list_received(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.get(Project, project_id)
    if project is None or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="project_not_found")
    return _received.get(project_id, [])
