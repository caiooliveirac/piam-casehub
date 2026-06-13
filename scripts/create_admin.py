"""Create or update the admin web user with a hashed password.

Usage:
    python scripts/create_admin.py [username] [password]

If args are omitted, ADMIN_USERNAME / ADMIN_PASSWORD from the environment are
used. Run inside the app container after migrations:
    docker compose exec web python scripts/create_admin.py
"""

from __future__ import annotations

import os
import sys

# Ensure the project root is importable when run as a plain script (the cwd
# inside the container is /app, but sys.path[0] would be /app/scripts).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402

from app.config import settings  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models.user import AdminUser  # noqa: E402
from app.web.auth import hash_password  # noqa: E402


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
