"""Admin authentication: password hashing + session-based login guard.

Uses PBKDF2-HMAC-SHA256 from the standard library to avoid extra native deps.
Sessions are signed cookies (Starlette SessionMiddleware) keyed by SECRET_KEY.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from base64 import b64decode, b64encode

from fastapi import Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models.user import AdminUser

_ITERATIONS = 200_000
_ALGO = "pbkdf2_sha256"


def hash_password(password: str) -> str:
    """Return a self-describing hash: pbkdf2_sha256$iters$salt$hash."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"{_ALGO}${_ITERATIONS}${b64encode(salt).decode()}${b64encode(dk).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algo, iters, salt_b64, hash_b64 = encoded.split("$")
        if algo != _ALGO:
            return False
        salt = b64decode(salt_b64)
        expected = b64decode(hash_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iters))
        return hmac.compare_digest(dk, expected)
    except (ValueError, TypeError):
        return False


def authenticate(username: str, password: str) -> bool:
    """Check credentials against the DB admin user, falling back to .env admin.

    The .env fallback guarantees first-login access even before create_admin.py
    has been run. It is compared in constant time.
    """
    with SessionLocal() as session:
        user = session.execute(
            select(AdminUser).where(AdminUser.username == username)
        ).scalar_one_or_none()
    if user and verify_password(password, user.password_hash):
        return True
    # Env fallback
    env_user_ok = hmac.compare_digest(username, settings.admin_username)
    env_pass_ok = hmac.compare_digest(password, settings.admin_password)
    return env_user_ok and env_pass_ok


def login_session(request: Request, username: str) -> None:
    request.session["user"] = username


def logout_session(request: Request) -> None:
    request.session.pop("user", None)


def current_user(request: Request) -> str | None:
    return request.session.get("user")


def require_login(request: Request) -> str | RedirectResponse:
    """Dependency: return username or a redirect to /login."""
    user = current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return user
