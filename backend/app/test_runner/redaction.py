"""Secret redaction.

Runs BEFORE a trace is stored and BEFORE any data is sent to the LLM.
Strips sensitive headers/body fields so secrets never hit logs or the model.
"""

import re

# Header names whose values must be fully redacted.
SENSITIVE_HEADERS = {
    "authorization",
    "x-api-key",
    "x-access-token",
    "x-auth-token",
    "cookie",
    "set-cookie",
    "proxy-authorization",
}

REDACTED = "***REDACTED***"

# Body field names (case-insensitive) to redact.
SENSITIVE_BODY_FIELDS = {
    "password",
    "client_secret",
    "api_key",
    "access_token",
    "refresh_token",
    "token",
    "secret",
    "webhook_secret",
}


def redact_headers(headers: dict) -> dict:
    out = {}
    for k, v in headers.items():
        if k.lower() in SENSITIVE_HEADERS:
            out[k] = REDACTED
        else:
            out[k] = v
    return out


def _redact_value(key: str, value):
    if isinstance(key, str) and key.lower() in SENSITIVE_BODY_FIELDS:
        return REDACTED
    return value


def redact_body(body):
    """Recursively redact sensitive keys in dict/list/primitive bodies."""
    if isinstance(body, dict):
        return {k: _redact_value(k, redact_body(v)) for k, v in body.items()}
    if isinstance(body, list):
        return [redact_body(v) for v in body]
    return body


def redact_trace(trace: dict) -> dict:
    """Redact a full request/response trace dict."""
    out = dict(trace)
    if "request_headers" in out:
        out["request_headers"] = redact_headers(out["request_headers"])
    if "response_headers" in out:
        out["response_headers"] = redact_headers(out["response_headers"])
    if "request_body" in out:
        out["request_body"] = redact_body(out["request_body"])
    return out
