"""Docs ingestion + retrieval routes (Day 8-9)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path

from app.core.database import get_db
from app.models import User
from app.api.dependencies import get_current_user
from app.docs.store import ingest, search

router = APIRouter(prefix="/api/v1/docs", tags=["docs"])

_SEED_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "seed_guide.txt"


@router.post("/ingest")
def ingest_doc(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    text = body.get("text")
    source = body.get("source", "manual")
    if not text:
        raise HTTPException(status_code=400, detail="text_required")
    n = ingest(text, source)
    return {"ingested_chunks": n, "source": source}


@router.post("/seed")
def seed_guide(current_user: User = Depends(get_current_user)):
    """Load the bundled game-commerce integration guide into the store."""
    text = _SEED_PATH.read_text(encoding="utf-8")
    n = ingest(text, source="seed_guide")
    return {"ingested_chunks": n, "source": "seed_guide"}


@router.get("/search")
def doc_search(q: str, limit: int = 5, current_user: User = Depends(get_current_user)):
    results = search(q, limit=limit)
    return {"query": q, "results": results}
