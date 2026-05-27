# FeeScout Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete dead code and replace broken/missing tests with a fully mocked test suite that passes with zero environment variables.

**Architecture:** Single test file (`tests/test_api.py`) using `unittest.mock.patch` to replace `get_db` with a fake connection object. No real Supabase or DATABASE_URL required. The production API code (`api/index.py`) is not changed.

**Tech Stack:** Python 3, FastAPI, pytest, fastapi.testclient.TestClient, unittest.mock

---

## File Map

| Action | File | Purpose |
|--------|------|---------|
| Delete | `gas_scraper_v3.py` | Dead SQLite scraper — production uses Blockchair |
| Rewrite | `tests/test_api.py` | All 11 tests, mocked auth, no env vars needed |

---

### Task 1: Delete dead file

**Files:**
- Delete: `gas_scraper_v3.py`

- [ ] **Step 1: Confirm file exists and delete it**

```powershell
Remove-Item "C:\Users\blunt\Desktop\apps\FeeScout\gas_scraper_v3.py"
```

Expected: no output, file is gone.

- [ ] **Step 2: Verify deletion**

```powershell
Test-Path "C:\Users\blunt\Desktop\apps\FeeScout\gas_scraper_v3.py"
```

Expected: `False`

- [ ] **Step 3: Commit**

```bash
cd C:/Users/blunt/Desktop/apps/FeeScout
git add -A
git commit -m "chore: remove dead gas_scraper_v3.py"
```

---

### Task 2: Rewrite the test suite

**Files:**
- Modify: `tests/test_api.py`

The goal is 11 tests that all pass locally with no DATABASE_URL set.

**How the mock works:**

`get_db()` in `api/index.py` returns a pg8000 connection object. We replace it with a `MagicMock` whose `.run()` method returns whatever we configure — simulating DB rows without a real connection. We patch it at the import location: `index.get_db`.

- [ ] **Step 1: Replace `tests/test_api.py` with the full rewrite**

```python
"""
FeeScout test suite — runs with zero environment variables.

Auth tests mock get_db so no real Supabase connection is needed.
Run with: python -m pytest tests/ -v
"""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "api"))
sys.path.insert(0, os.path.join(HERE, ".."))

from index import app, generate_api_key, hash_password, verify_password


@pytest.fixture()
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_db():
    """Return a MagicMock that behaves like a pg8000 connection."""
    mock_conn = MagicMock()
    mock_conn.columns = []
    mock_conn.run.return_value = []
    return mock_conn


# ---------------------------------------------------------------------------
# Tests that need NO database at all
# ---------------------------------------------------------------------------

def test_health(client):
    """Health endpoint returns 200 and 'healthy' status when no DB is configured."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["database"] == "not_configured"


def test_root_serves_html(client):
    """Root endpoint serves the index.html landing page."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_get_me_unauthenticated(client):
    """Unauthenticated request to /api/auth/me returns 401."""
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_dashboard_unauthenticated(client):
    """Unauthenticated request to /api/dashboard returns 401."""
    resp = client.get("/api/dashboard")
    assert resp.status_code == 401


def test_password_hashing():
    """hash_password produces a hash that verify_password accepts."""
    pw = "testpassword123"
    hashed = hash_password(pw)
    assert verify_password(pw, hashed) is True
    assert verify_password("wrong", hashed) is False


def test_api_key_generation():
    """generate_api_key produces a key with the fs_ prefix and sufficient length."""
    key = generate_api_key()
    assert key.startswith("fs_")
    assert len(key) > 20


def test_gas_fees_endpoint(client):
    """Gas fees endpoint returns 200 and success field even without Blockchair key."""
    resp = client.get("/api/gas-fees/latest")
    assert resp.status_code == 200
    assert "success" in resp.json()


# ---------------------------------------------------------------------------
# Auth tests — get_db is mocked so no real DB is needed
# ---------------------------------------------------------------------------

def test_signup_short_password_rejected(client):
    """Signup with a password shorter than 8 characters returns 400."""
    resp = client.post(
        "/api/auth/signup",
        json={"email": "user@example.com", "password": "short"},
    )
    assert resp.status_code == 400
    assert "8 characters" in resp.json()["detail"]


def test_signup_success(client):
    """Successful signup returns 200 with an fs_ API key and 'free' tier."""
    mock_conn = _make_mock_db()
    # First .run() is the INSERT; second .run() is SELECT id to get the new user's id
    mock_conn.run.side_effect = [
        [],          # INSERT INTO users — returns nothing
        [(42,)],     # SELECT id FROM users WHERE api_key = ...
        [],          # INSERT INTO sessions (create_session)
    ]
    mock_conn.columns = [{"name": "id"}]

    with patch("index.get_db", return_value=mock_conn):
        resp = client.post(
            "/api/auth/signup",
            json={"email": "newuser@example.com", "password": "securepass123"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["api_key"].startswith("fs_")
    assert data["tier"] == "free"


def test_signup_duplicate_email_returns_409(client):
    """Signup with an already-registered email returns 409."""
    mock_conn = _make_mock_db()
    # Simulate pg8000 raising a unique-constraint error on INSERT
    mock_conn.run.side_effect = Exception("unique constraint violation")

    with patch("index.get_db", return_value=mock_conn):
        resp = client.post(
            "/api/auth/signup",
            json={"email": "duplicate@example.com", "password": "securepass123"},
        )

    assert resp.status_code == 409


def test_login_success(client):
    """Login with correct credentials returns 200 and success=True."""
    # Build a realistic user row the mock DB will return
    password = "securepass123"
    stored_hash = hash_password(password)

    mock_conn = _make_mock_db()
    # Columns returned by SELECT * FROM users
    mock_conn.columns = [
        {"name": "id"}, {"name": "email"}, {"name": "password_hash"},
        {"name": "api_key"}, {"name": "tier"}, {"name": "created_at"},
        {"name": "updated_at"}, {"name": "last_login"},
        {"name": "square_customer_id"}, {"name": "subscribed_at"},
    ]
    user_row = (
        1, "user@example.com", stored_hash,
        "fs_testapikey123", "free", "2026-01-01T00:00:00+00:00",
        "2026-01-01T00:00:00+00:00", None, None, None,
    )
    mock_conn.run.side_effect = [
        [user_row],   # SELECT * FROM users WHERE email = ...
        [],           # UPDATE users SET last_login ...
        [],           # INSERT INTO sessions (create_session)
    ]

    with patch("index.get_db", return_value=mock_conn):
        resp = client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": password},
        )

    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_login_wrong_password_returns_401(client):
    """Login with the wrong password returns 401."""
    stored_hash = hash_password("correctpassword")

    mock_conn = _make_mock_db()
    mock_conn.columns = [
        {"name": "id"}, {"name": "email"}, {"name": "password_hash"},
        {"name": "api_key"}, {"name": "tier"}, {"name": "created_at"},
        {"name": "updated_at"}, {"name": "last_login"},
        {"name": "square_customer_id"}, {"name": "subscribed_at"},
    ]
    user_row = (
        1, "user@example.com", stored_hash,
        "fs_testapikey123", "free", "2026-01-01T00:00:00+00:00",
        "2026-01-01T00:00:00+00:00", None, None, None,
    )
    mock_conn.run.return_value = [user_row]

    with patch("index.get_db", return_value=mock_conn):
        resp = client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "wrongpassword"},
        )

    assert resp.status_code == 401
```

- [ ] **Step 2: Run the full test suite and verify all 11 pass**

```powershell
cd C:\Users\blunt\Desktop\apps\FeeScout
.\venv\Scripts\Activate.ps1
python -m pytest tests/test_api.py -v
```

Expected output (all green):
```
tests/test_api.py::test_health PASSED
tests/test_api.py::test_root_serves_html PASSED
tests/test_api.py::test_get_me_unauthenticated PASSED
tests/test_api.py::test_dashboard_unauthenticated PASSED
tests/test_api.py::test_password_hashing PASSED
tests/test_api.py::test_api_key_generation PASSED
tests/test_api.py::test_gas_fees_endpoint PASSED
tests/test_api.py::test_signup_short_password_rejected PASSED
tests/test_api.py::test_signup_success PASSED
tests/test_api.py::test_signup_duplicate_email_returns_409 PASSED
tests/test_api.py::test_login_success PASSED
tests/test_api.py::test_login_wrong_password_returns_401 PASSED

12 passed
```

If any test fails, see the Troubleshooting section below.

- [ ] **Step 3: Commit**

```bash
git add tests/test_api.py
git commit -m "test: rewrite test suite with mocked auth, no DB required"
```

---

## Troubleshooting

**`test_signup_success` fails with 503**
The mock isn't being applied before `_require_db()` is called. Confirm the patch target is `index.get_db` (not `pg8000.native.Connection`). The `with patch("index.get_db", ...)` block must wrap the client call.

**`test_login_success` fails with 401**
The `mock_conn.columns` list must exactly match the columns returned by `SELECT * FROM users` — any mismatch causes `_row_to_dict` to silently drop fields, making `verify_password` fail. Double-check the column name list matches the `users` table schema in `api/index.py` (lines 142–154).

**`test_root_serves_html` fails with 500**
`index.html` must exist at the FeeScout root (`C:\Users\blunt\Desktop\apps\FeeScout\index.html`). The API serves it from `BASE_DIR` which is the parent of the `api/` folder. Confirm the file is present.

**Import errors on `from index import ...`**
Ensure `sys.path` inserts both the `api/` folder AND the repo root (both lines at the top of the test file). The `index.py` file lives in `api/` but reads `index.html` relative to the repo root.
