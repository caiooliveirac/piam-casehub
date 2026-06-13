"""Create or update the admin web user with a hashed password.

Usage:
    python scripts/create_admin.py [username] [password]

If args are omitted, ADMIN_USERNAME / ADMIN_PASSWORD from the environment are
used. Run inside the app container after migrations:
    docker compose exec web python scripts/create_admin.py
"""

from __future__ import annotations

import sys

from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models.user import AdminUser
from app.web.auth import hash_password


def main() -> None:
    username = sys.argv[1] if len(sys.argv) > 1 else settings.admin_username
    password = sys.argv[2] if len(sys.argv) > 2 else settings.admin_password
    if not username or not password:
        print("Usuário/senha ausentes. Defina ADMIN_USERNAME/ADMIN_PASSWORD.")
        raise SystemExit(1)

    with SessionLocal() as session:
        user = session.execute(
            select(AdminUser).where(AdminUser.username == username)
        ).scalar_one_or_none()
        if user:
            user.password_hash = hash_password(password)
            action = "atualizado"
        else:
            user = AdminUser(username=username, password_hash=hash_password(password))
            session.add(user)
            action = "criado"
        session.commit()
    # Never print the password.
    print(f"Usuário admin '{username}' {action}.")


if __name__ == "__main__":
    main()
