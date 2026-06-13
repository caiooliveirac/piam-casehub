"""App-level tests: health endpoint, case creation public_id, .env not tracked."""

from __future__ import annotations

import subprocess

from fastapi.testclient import TestClient

from app.main import app


def test_health_responds():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_case_creation_generates_public_id(session):
    from app.services.telegram_ingest import create_case_from_text

    case = create_case_from_text(session, "Idade: 60 anos\nPA: 100/70 mmHg")
    assert case.public_id.startswith("PIAM-")
    assert case.status == "novo"
    # Sequential second case increments the counter.
    case2 = create_case_from_text(session, "Idade: 50 anos")
    assert case2.public_id != case.public_id


def test_env_not_tracked_by_git():
    # .env must never be tracked. If git isn't initialised yet, this is vacuously
    # safe (no tracked files at all), so we only fail when .env IS tracked.
    result = subprocess.run(
        ["git", "ls-files", ".env"],
        capture_output=True,
        text=True,
    )
    tracked = result.stdout.strip()
    assert tracked == "", f".env está versionado: {tracked!r}"
