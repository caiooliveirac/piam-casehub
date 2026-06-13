"""Audit helper — single chokepoint for recording auditable actions."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def record(
    session: Session,
    *,
    action: str,
    actor_type: str = "system",
    actor_id: str | None = None,
    case_id: int | None = None,
    payload: dict[str, Any] | None = None,
    commit: bool = True,
) -> AuditLog:
    """Persist an audit entry. Payload is JSON-serialised; never store secrets."""
    log = AuditLog(
        action=action,
        actor_type=actor_type,
        actor_id=actor_id,
        case_id=case_id,
        payload_json=json.dumps(payload, ensure_ascii=False) if payload else None,
    )
    session.add(log)
    if commit:
        session.commit()
    return log
