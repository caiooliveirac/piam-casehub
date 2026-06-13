"""Web rendering/redirect tests.

These exercise actual Jinja template rendering — the gap that previously let a
broken TemplateResponse signature reach production (only /health was tested).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_login_page_renders():
    # Renders login.html through Jinja — catches TemplateResponse misuse.
    resp = client.get("/login")
    assert resp.status_code == 200
    assert "Acesso administrativo" in resp.text


def test_root_redirects_to_login_when_anonymous():
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_dashboard_requires_login():
    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_metrics_requires_login():
    resp = client.get("/metrics", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"
