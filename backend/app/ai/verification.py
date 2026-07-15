"""Verification engine (Day 13).

The core thesis: an AI-suggested fix is NOT trusted until a deterministic test
proves it. This service re-runs the fix's `verification_test` against the target
and records verified / unverified. With the mock (which we don't mutate), a fix
stays unverified — correctly — until a real fix is applied. This is what
separates GameBridge from "ask the AI and hope".
"""

from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models import SuggestedFix, Diagnosis, TestRun, VerificationRun, Project
from app.test_runner.executor import execute_test
from app.test_runner.registry import BUILTIN_TESTS
from app.core.config import settings


async def verify_fix(db: Session, fix_id: int) -> VerificationRun:
    fix = db.get(SuggestedFix, fix_id)
    if fix is None:
        raise ValueError("fix_not_found")

    # find the test definition by name in the registry
    test_def = next((t for t in BUILTIN_TESTS if t["name"] == fix.verification_test), None)

    # we re-run against a fresh project-shaped run to record the verification
    diag = db.get(Diagnosis, fix.diagnosis_id)
    run = db.get(TestRun, diag.test_run_id)

    if test_def is None:
        vr = VerificationRun(fix_id=fix_id, test_run_id=run.id, status="error",
                             notes=f"verification_test not found: {fix.verification_test}")
        db.add(vr)
        db.commit()
        return vr

    result = await execute_test(
        settings.mock_api_base,
        test_def,
        headers=test_def.get("headers"),
        inject_failure_mode=test_def.get("failure_mode"),
        timeout_seconds=test_def.get("timeout_seconds", 10),
    )

    # A fix is "verified" only if re-running its verification test now PASSES.
    # Since the underlying integration is unchanged, a still-failing test =>
    # unverified (honest). A passing test => verified.
    status = "verified" if result.passed else "unverified"
    vr = VerificationRun(
        fix_id=fix_id,
        test_run_id=run.id,
        status=status,
        rerun_response_status=result.trace.response_status,
        notes=f"reran '{fix.verification_test}': expected {test_def['expected_status']}, "
              f"got {result.trace.response_status} -> {status}",
    )
    db.add(vr)
    db.commit()
    db.refresh(vr)
    return vr
