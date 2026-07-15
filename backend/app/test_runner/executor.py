"""Test runner executor.

Builds an HTTP request from a test definition, sends it through the active
CommerceAdapter, captures a full request/response trace (with secret redaction),
and validates the result against the test's expected definition.
"""

from dataclasses import dataclass, field
from time import monotonic
import httpx

from app.test_runner.redaction import redact_trace


@dataclass
class Trace:
    method: str
    url: str
    request_headers: dict
    request_body: dict | None
    response_status: int | None
    response_headers: dict
    response_body: dict | None
    duration_ms: int
    status: str = "ok"  # ok | error
    error_type: str | None = None

    def to_dict(self) -> dict:
        d = {
            "method": self.method,
            "url": self.url,
            "request_headers": self.request_headers,
            "request_body": self.request_body,
            "response_status": self.response_status,
            "response_headers": self.response_headers,
            "response_body": self.response_body,
            "duration_ms": self.duration_ms,
            "status": self.status,
        }
        if self.error_type:
            d["error_type"] = self.error_type
        return redact_trace(d)


@dataclass
class RunResult:
    passed: bool
    trace: Trace
    detail: str = ""


async def execute_test(
    base_url: str,
    test_def: dict,
    headers: dict | None = None,
    inject_failure_mode: str | None = None,
    timeout_seconds: int = 10,
) -> RunResult:
    """Execute one test definition against the target adapter base URL."""
    method = test_def.get("method", "GET").upper()
    path = test_def.get("path", "/")
    expected_status = test_def.get("expected_status", 200)
    body = test_def.get("body")

    req_headers = dict(headers or {})
    if inject_failure_mode:
        req_headers["X-Failure-Mode"] = inject_failure_mode

    url = f"{base_url.rstrip('/')}{path}"
    start = monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.request(
                method, url,
                headers=req_headers,
                json=body if body is not None else None,
            )
        duration_ms = int((monotonic() - start) * 1000)
        try:
            resp_body = resp.json()
        except Exception:
            resp_body = {"_raw": resp.text[:500]}
        trace = Trace(
            method=method, url=url,
            request_headers=req_headers,
            request_body=body,
            response_status=resp.status_code,
            response_headers=dict(resp.headers),
            response_body=resp_body,
            duration_ms=duration_ms,
        )
        passed = resp.status_code == expected_status
        return RunResult(passed, trace, detail=f"expected {expected_status}, got {resp.status_code}")
    except httpx.TimeoutException:
        duration_ms = int((monotonic() - start) * 1000)
        trace = Trace(
            method=method, url=url, request_headers=req_headers, request_body=body,
            response_status=None, response_headers={}, response_body=None,
            duration_ms=duration_ms, status="error", error_type="timeout",
        )
        return RunResult(False, trace, detail="request timed out")
    except Exception as e:
        duration_ms = int((monotonic() - start) * 1000)
        trace = Trace(
            method=method, url=url, request_headers=req_headers, request_body=body,
            response_status=None, response_headers={}, response_body=None,
            duration_ms=duration_ms, status="error", error_type=type(e).__name__,
        )
        return RunResult(False, trace, detail=str(e)[:200])
