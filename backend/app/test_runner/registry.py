"""Built-in test definitions (the seed catalog).

Each maps to a scenario in the evaluation set (§18). `failure_mode` is the
X-Failure-Mode header sent to the mock to provoke the exact failure the test
expects to catch.
"""

BUILTIN_TESTS = [
    {
        "name": "Fetch catalog with valid token",
        "category": "catalog",
        "method": "GET",
        "path": "/mock/catalog",
        "expected_status": 200,
        "headers": {"Authorization": "Bearer valid_token_abc"},
        "body": None,
        "failure_mode": None,
    },
    {
        "name": "Fetch catalog with missing token",
        "category": "catalog",
        "method": "GET",
        "path": "/mock/catalog",
        "expected_status": 401,
        "headers": {},
        "body": None,
        "failure_mode": None,
    },
    {
        "name": "Fetch catalog with invalid token",
        "category": "catalog",
        "method": "GET",
        "path": "/mock/catalog",
        "expected_status": 401,
        "headers": {"Authorization": "Bearer valid_token_abc"},
        "body": None,
        "failure_mode": "invalid-token",
    },
    {
        "name": "Fetch catalog with expired token",
        "category": "catalog",
        "method": "GET",
        "path": "/mock/catalog",
        "expected_status": 401,
        "headers": {"Authorization": "Bearer expired_token_123"},
        "body": None,
        "failure_mode": None,
    },
    {
        "name": "Create order with valid token",
        "category": "orders",
        "method": "POST",
        "path": "/mock/orders",
        "expected_status": 200,
        "headers": {"Authorization": "Bearer valid_token_abc"},
        "body": {"sku": "gold_100"},
        "failure_mode": None,
    },
    {
        "name": "Create order with missing sku",
        "category": "orders",
        "method": "POST",
        "path": "/mock/orders",
        "expected_status": 400,
        "headers": {"Authorization": "Bearer valid_token_abc"},
        "body": {},
        "failure_mode": None,
    },
    {
        "name": "Issue auth token",
        "category": "auth",
        "method": "POST",
        "path": "/mock/auth/token",
        "expected_status": 200,
        "headers": {"Content-Type": "application/json"},
        "body": {"client_id": "demo"},
        "failure_mode": None,
    },
]
