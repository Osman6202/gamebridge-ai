"""Verification routes (Day 13)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import User, Project, SuggestedFix
from app.api.dependencies import get_current_user
from app.ai.verification import verify_fix

router = APIRouter(prefix="/api/v1/projects", tags=["verification"])


@router.post("/{project_id}/fixes/{fix_id}/verify")
async def verify(
    project_id: int,
    fix_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.get(Project, project_id)
    if project is None or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="project_not_found")
    fix = db.get(SuggestedFix, fix_id)
    if fix is None:
        raise HTTPException(status_code=404, detail="fix_not_found")
    vr = await verify_fix(db, fix_id)
    return {
        "verification_run_id": vr.id,
        "status": vr.status,
        "rerun_response_status": vr.rerun_response_status,
        "notes": vr.notes,
    }
