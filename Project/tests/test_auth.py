"""Logged-out requests must be rejected. Run from the repo root: python -m pytest Project/tests"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app  # noqa: E402

API_ENDPOINTS = [
    ("GET", "/api/test"),
    ("GET", "/api/process_emails_stream"),
    ("POST", "/api/calendar/events"),
    ("POST", "/api/process_emails"),
    ("POST", "/api/parse_text"),
]


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_index_redirects_to_login(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_login_page_has_csrf_token(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b'name="csrf_token"' in response.data


@pytest.mark.parametrize("method,path", API_ENDPOINTS)
def test_api_rejects_logged_out_requests(client, method, path):
    response = client.open(path, method=method, json={})
    # GETs fail the login check (401); POSTs fail the CSRF check first (400)
    assert response.status_code in (400, 401)
    assert "error" in response.get_json()


@pytest.mark.parametrize("method,path", API_ENDPOINTS)
def test_api_rejects_logged_out_requests_without_csrf(client, method, path):
    # Even with CSRF turned off, a logged-out caller must get a 401
    app.config["WTF_CSRF_ENABLED"] = False
    try:
        response = client.open(path, method=method, json={})
    finally:
        app.config["WTF_CSRF_ENABLED"] = True
    assert response.status_code == 401


def test_login_post_without_csrf_token_is_rejected(client):
    response = client.post("/login", data={"username": "someone", "password": "x"})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    # Not logged in afterwards
    assert client.get("/").status_code == 302


def test_logout_requires_login(client):
    app.config["WTF_CSRF_ENABLED"] = False
    try:
        response = client.post("/logout")
    finally:
        app.config["WTF_CSRF_ENABLED"] = True
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
