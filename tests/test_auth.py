"""Auth tests: password hashing and the .env-fallback safety gate."""

from __future__ import annotations

from app.config import settings
from app.web import auth


def test_hash_and_verify_roundtrip():
    h = auth.hash_password("s3nha-forte")
    assert h.startswith("pbkdf2_sha256$")
    assert auth.verify_password("s3nha-forte", h)
    assert not auth.verify_password("errada", h)


def test_verify_rejects_malformed_hash():
    assert not auth.verify_password("x", "not-a-valid-hash")


def test_env_fallback_blocked_for_default_password(monkeypatch):
    # With a placeholder password, the .env fallback must never authenticate.
    monkeypatch.setattr(settings, "admin_username", "admin")
    monkeypatch.setattr(settings, "admin_password", "change-me")
    assert auth.authenticate("admin", "change-me") is False


def test_env_fallback_works_with_real_password(monkeypatch):
    monkeypatch.setattr(settings, "admin_username", "admin")
    monkeypatch.setattr(settings, "admin_password", "uma-senha-de-verdade")
    assert auth.authenticate("admin", "uma-senha-de-verdade") is True
    assert auth.authenticate("admin", "outra") is False
