"""Diagnosis + fix routes (Day 10-12).

Flow: given a failed test run, call the local/free LLM to diagnose, then generate
suggested fixes. Both steps have safety rails (parse failure -> stored marker,
no crash). This is the AI layer; it sits ON TOP of the deterministic test/verify
core and is never trusted on its own.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import User, Project, TestRun
from app.api.dependencies import get_current_user
from app.ai.diagnosis import diagnose_test_run
from app.ai.fixes import suggest_fixes_for
from app.ai.provider import LLMConfig

router = APIRouter(prefix="/api/v1/projects", tags=["diagnosis"])

# default: local/free Hermes API (hy3:free). Override provider via query.
DEFAULT_CFG = LLMConfig()


async def _own_test_run(db, project_id, test_run_id, current_user):
    run = db.get(TestRun, test_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="test_run_not_found")
    project = db.get(Project, project_id)
    if project is None or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="project_not_found")
    return run


@router.post("/{project_id}/test-runs/{test_run_id}/diagnose")
async def diagnose(
    project_id: int,
    test_run_id: int,
    provider: str = "hermes",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _own_test_run(db, project_id, test_run_id, current_user)
    cfg = LLMConfig(provider=provider) if provider != "hermes" else DEFAULT_CFG
    diag = await diagnose_test_run(db, test_run_id, cfg)
    return {
        "diagnosis_id": diag.id,
        "problem": diag.problem,
        "root_cause": diag.root_cause,
        "evidence": diag.evidence,
        "confidence": diag.confidence,
    }


@router.post("/{project_id}/diagnoses/{diagnosis_id}/fixes")
async def suggest_fixes(
    project_id: int,
    diagnosis_id: int,
    provider: str = "hermes",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.get(Project, project_id)
    if project is None or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="project_not_found")
    cfg = LLMConfig(provider=provider) if provider != "hermes" else DEFAULT_CFG
    fixes = await suggest_fixes_for(db, diagnosis_id, cfg)
    return [
        {"id": f.id, "fix_type": f.fix_type, "description": f.description,
         "code": f.code, "verification_test": f.verification_test}
        for f in fixes
    ]
