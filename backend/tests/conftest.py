"""
Shared fixtures for DAItaView E2E tests.

These tests run against a live stack (docker-compose up).
Set TEST_BASE_URL in the environment to override the default.
"""
import os
import pytest
import httpx

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")

ADMIN_EMAIL = os.getenv("SUPERADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("SUPERADMIN_PASSWORD", "change-me-immediately")


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def admin_token(base_url: str) -> str:
    r = httpx.post(f"{base_url}/auth/login", json={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    r.raise_for_status()
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def admin_client(base_url: str, admin_token: str) -> httpx.Client:
    return httpx.Client(base_url=base_url, headers={"Authorization": f"Bearer {admin_token}"}, timeout=60)
