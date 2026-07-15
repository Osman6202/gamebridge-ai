"""Test execution routes.

Runs built-in test definitions against the mock commerce API (or sandbox later)
and persists TestRun + RequestTrace records. No AI involved — this is the
core verification loop that the diagnosis layer later explains.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import asyncio

from app.core.database import get_db
from app.models import User, Project, TestRun, RequestTrace
from app.api.dependencies import get_current_user
from app.test_runner.registry import BUILTIN_TESTS
from app.test_runner.executor import execute_test
from app.core.config import settings

router = APIRouter(prefix="/api/v1/projects", tags=["tests"])


@router.get("/{project_id}/tests/available")
def available_tests():
    return [{"name": t["name"], "category": t["category"]} for t in BUILTIN_TESTS]


@router.post("/{project_id}/tests/run")
async def run_test(
    project_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # project ownership check
    project = db.get(Project, project_id)
    if project is None or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="project_not_found")

    test_name = body.get("test_name")
    test_def = next((t for t in BUILTIN_TESTS if t["name"] == test_name), None)
    if test_def is None:
        raise HTTPException(status_code=404, detail="test_not_found")

    base_url = settings.mock_api_base
    result = await execute_test(
        base_url,
        test_def,
        headers=test_def.get("headers"),
        inject_failure_mode=test_def.get("failure_mode"),
        timeout_seconds=test_def.get("timeout_seconds", 10),
    )

    # persist
    run = TestRun(
        project_id=project_id,
        test_case_id=0,  # builtin (no DB TestCase row yet for MVP)
        status="passed" if result.passed else "failed",
        duration_ms=result.trace.duration_ms,
        error_type=result.trace.error_type,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    trace = RequestTrace(
        test_run_id=run.id,
        method=result.trace.method,
        url=result.trace.url,
        request_headers=result.trace.to_dict()["request_headers"],
        request_body=result.trace.request_body,
        response_status=result.trace.response_status,
        response_headers=result.trace.to_dict()["response_headers"],
        response_body=result.trace.response_body,
        duration_ms=result.trace.duration_ms,
        status=result.trace.status,
    )
    db.add(trace)
    db.commit()

    return {
        "test_run_id": run.id,
        "passed": result.passed,
        "detail": result.detail,
        "trace": result.trace.to_dict(),
    }


@router.get("/{project_id}/test-runs")
def list_runs(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.get(Project, project_id)
    if project is None or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="project_not_found")
    runs = db.query(TestRun).filter(TestRun.project_id == project_id).order_by(TestRun.id.desc()).all()
    return [
        {"id": r.id, "status": r.status, "duration_ms": r.duration_ms, "error_type": r.error_type}
        for r in runs
    ]
