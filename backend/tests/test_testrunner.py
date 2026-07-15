"""Tests for the test runner + secret redaction (Day 4)."""

import pytest
from app.test_runner.redaction import redact_trace, redact_headers, redact_body
from app.test_runner.executor import execute_test, Trace, RunResult


def test_redact_headers():
    h = {"Authorization": "Bearer secret", "X-Api-Key": "abc", "Content-Type": "application/json"}
    out = redact_headers(h)
    assert out["Authorization"] == "***REDACTED***"
    assert out["X-Api-Key"] == "***REDACTED***"
    assert out["Content-Type"] == "application/json"


def test_redact_body_recursive():
    body = {"user": {"password": "hunter2", "name": "osman"}, "token": "xyz"}
    out = redact_body(body)
    assert out["user"]["password"] == "***REDACTED***"
    assert out["user"]["name"] == "osman"
    assert out["token"] == "***REDACTED***"


def test_redact_trace_masks_secrets():
    trace = {
        "method": "GET", "url": "http://x/catalog",
        "request_headers": {"Authorization": "Bearer real"},
        "request_body": {"client_secret": "top"},
        "response_headers": {"Set-Cookie": "sess=1"},
        "response_body": {"ok": True},
    }
    out = redact_trace(trace)
    assert out["request_headers"]["Authorization"] == "***REDACTED***"
    assert out["request_body"]["client_secret"] == "***REDACTED***"
    assert out["response_headers"]["Set-Cookie"] == "***REDACTED***"
    assert out["response_body"]["ok"] is True


@pytest.mark.asyncio
async def test_execute_valid_catalog():
    # Hits the real mock service if running; otherwise asserts structure.
    result = await execute_test(
        "http://127.0.0.1:8001",
        {"method": "GET", "path": "/mock/catalog", "expected_status": 200,
         "headers": {"Authorization": "Bearer valid_token_abc"}},
        headers={"Authorization": "Bearer valid_token_abc"},
    )
    assert isinstance(result, RunResult)
    assert result.trace.response_status == 200
    # redaction applied to the returned trace dict
    assert result.trace.to_dict()["request_headers"]["Authorization"] == "***REDACTED***"
