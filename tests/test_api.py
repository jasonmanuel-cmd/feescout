"""Test FeeScout API locally: python3 -m pytest tests/ -v"""
import sys
import os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "api"))
sys.path.insert(0, os.path.join(HERE, ".."))

from index import app, init_db, get_db, hash_password, verify_password, generate_api_key
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["service"] == "FeeScout API"


def test_signup():
    import uuid
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post("/api/auth/signup", json={"email": email, "password": "testpass123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["api_key"].startswith("fs_")
    assert data["tier"] == "free"
    return email


def test_login():
    import uuid
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    # Sign up first
    client.post("/api/auth/signup", json={"email": email, "password": "testpass123"})
    # Login
    resp = client.post("/api/auth/login", json={"email": email, "password": "testpass123"})
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_login_wrong_password():
    import uuid
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/auth/signup", json={"email": email, "password": "testpass123"})
    resp = client.post("/api/auth/login", json={"email": email, "password": "wrongpass"})
    assert resp.status_code == 401


def test_get_me_unauthenticated():
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_dashboard_unauthenticated():
    resp = client.get("/api/dashboard")
    assert resp.status_code == 401


def test_password_hashing():
    pw = "testpassword123"
    hashed = hash_password(pw)
    assert verify_password(pw, hashed) is True
    assert verify_password("wrong", hashed) is False


def test_api_key_generation():
    key = generate_api_key()
    assert key.startswith("fs_")
    assert len(key) > 20


def test_signup_duplicate_email():
    import uuid
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/auth/signup", json={"email": email, "password": "testpass123"})
    resp = client.post("/api/auth/signup", json={"email": email, "password": "testpass123"})
    assert resp.status_code == 409


def test_gas_fees_endpoint():
    resp = client.get("/api/gas-fees/latest")
    # Should return 200 even without Blockchair key (empty data)
    assert resp.status_code == 200
    data = resp.json()
    assert "success" in data


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
