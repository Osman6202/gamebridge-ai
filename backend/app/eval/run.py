"""Evaluation harness (Day 16).

Measures how well the AI diagnosis + fixes perform across the canonical failure
modes. This is the evidence for "I confirmed the AI actually worked" — concrete
metrics, not vibes.

Run: python -m app.eval.run
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models import *  # noqa
from app.test_runner.executor import execute_test
from app.test_runner.registry import BUILTIN_TESTS
from app.core.config import settings
from app.ai.diagnosis import diagnose_test_run
from app.ai.fixes import suggest_fixes_for
import asyncio


# Ground truth: for each FAILING test, the root-cause keyword we expect the
# diagnosis to surface. Tests that return 200 despite a failure_mode are treated
# as passing (the mock can't truly fail them) and skipped for diagnosis scoring.
EXPECTED = {
    "Fetch catalog with invalid token": "invalid token",
    "Fetch catalog with expired token": "expired",
    "Fetch catalog with wrong api version": "api version",
    "Fetch catalog rate limited": "rate",
    "Fetch catalog server error": "500",
    "Create order with missing sku": "sku",
    "Create order with unknown sku": "unknown sku",
    "Create order with invalid state": "order state",
    "Create order wrong method": "405",
    "Issue auth token missing field": "client_id",
    "Webhook with bad signature": "signature",
    "Webhook duplicate event": "duplicate",
    "Create order that times out": "timeout",
}


def _make_session():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)()


async def run_eval() -> dict:
    rows = []
    sess = _make_session()

    # a throwaway project so diagnoses have somewhere to attach
    proj = Project(name="eval", user_id=1, framework="generic", environment="mock")
    sess.add(proj)
    sess.commit()
    cfg = None  # use default Ollama

    # build a TestCase per builtin test so TestRun FK is valid
    name_to_case = {}
    for t in BUILTIN_TESTS:
        tc = TestCase(name=t["name"], category=t.get("category", "general"),
                      request_definition=t, expected_definition={"expected_status": t.get("expected_status")})
        sess.add(tc)
        sess.commit()
        sess.refresh(tc)
        name_to_case[t["name"]] = tc.id

    for name, _ in {t["name"]: None for t in BUILTIN_TESTS}.items():
        defn = next((t for t in BUILTIN_TESTS if t["name"] == name), None)
        if defn is None:
            continue
        result = await execute_test(
            settings.mock_api_base, defn,
            headers=defn.get("headers"),
            inject_failure_mode=defn.get("failure_mode"),
            timeout_seconds=defn.get("timeout_seconds", 10),
        )
        tr = TestRun(project_id=proj.id, test_case_id=name_to_case[name],
                     status="passed" if result.passed else "failed",
                     duration_ms=result.trace.duration_ms,
                     error_type=result.trace.status if not result.passed else None)
        sess.add(tr)
        sess.commit()
        sess.refresh(tr)
        # persist trace
        trace = result.trace
        sess.add(RequestTrace(test_run_id=tr.id, method=trace.method, url=trace.url,
                              request_headers=trace.request_headers, request_body=trace.request_body,
                              response_status=trace.response_status, response_headers=trace.response_headers,
                              response_body=trace.response_body, duration_ms=trace.duration_ms,
                              status=trace.status))
        sess.commit()

        rec = {"test": name, "passed": result.passed, "expected_kw": EXPECTED.get(name, ""),
               "response_status": result.trace.response_status}
        # A diagnosis target = the CLIENT call failed (non-2xx). These are the
        # cases where an engineer would ask "why did my integration break?".
        is_failure = result.trace.response_status is None or result.trace.response_status < 200 or result.trace.response_status >= 300
        if is_failure:
            try:
                diag = await diagnose_test_run(sess, tr.id, cfg)
                rec["diagnosis_id"] = diag.id
                rec["root_cause"] = diag.root_cause
                rec["confidence"] = diag.confidence
                kw = EXPECTED.get(name, "")
                rec["hit"] = bool(kw) and (kw.lower() in (diag.root_cause or "").lower())
                try:
                    fixes = await suggest_fixes_for(sess, diag.id, cfg)
                    rec["fixes"] = len(fixes)
                except Exception:
                    rec["fixes"] = 0
            except Exception as e:
                rec["error"] = str(e)
        else:
            rec["note"] = "call succeeded (2xx) — not a diagnosis target"
        rows.append(rec)

    diagnosis_targets = [r for r in rows if r.get("root_cause")]
    hits = [r for r in diagnosis_targets if r.get("hit")]
    summary = {
        "total_tests": len(rows),
        "diagnosis_targets": len(diagnosis_targets),
        "diagnosis_hits": len(hits),
        "diagnosis_accuracy": round(len(hits) / max(len(diagnosis_targets), 1), 2),
        "avg_confidence": round(sum(r.get("confidence", 0) for r in diagnosis_targets) / max(len(diagnosis_targets), 1), 2),
        "rows": rows,
    }
    return summary


if __name__ == "__main__":
    out = asyncio.run(run_eval())
    print(f"Tests: {out['total_tests']} | Diagnosis targets: {out['diagnosis_targets']} | "
          f"Accuracy: {out['diagnosis_accuracy']*100:.0f}% | "
          f"Avg confidence: {out['avg_confidence']}")
    for r in out["rows"]:
        if r.get("root_cause"):
            tag = "OK " if r.get("hit") else "MISS"
            print(f"  [{tag}] {r['test']}: {r.get('root_cause','')[:70]} (conf {r.get('confidence',0)})")
        else:
            print(f"  [SKIP] {r['test']}: {r.get('note','')}")
