"""Ingestion pipeline: turn Telegram input into cases, messages, attachments.

This module is transport-agnostic — it takes plain values, not Telegram
objects — so it is easy to unit-test and reuse. The bot handlers (app/bot)
translate Telegram updates into calls here.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.case import OPEN_STATUSES, Case
from app.models.message import TelegramMessage
from app.schemas.case import ParsedCase
from app.services import audit
from app.services.case_parser import parse_case
from app.services.piam_formatter import format_from_parsed


def generate_public_id(session: Session) -> str:
    """Build a readable sequential id like PIAM-2026-000001 (per year)."""
    year = datetime.now(timezone.utc).year
    prefix = f"PIAM-{year}-"
    count = session.execute(
        select(func.count())
        .select_from(Case)
        .where(Case.public_id.like(f"{prefix}%"))
    ).scalar_one()
    return f"{prefix}{count + 1:06d}"


def _apply_parsed(case: Case, parsed: ParsedCase) -> None:
    """Copy parsed fields onto the case row."""
    case.patient_name = parsed.patient_name
    case.patient_age = parsed.patient_age
    case.patient_weight = parsed.patient_weight
    case.patient_birth_date = parsed.patient_birth_date
    case.companion = parsed.companion
    case.health_plan = parsed.health_plan
    case.origin_unit = parsed.origin_unit
    case.mp = parsed.mp
    case.admission_at = parsed.admission_at
    case.ecg_at = parsed.ecg_at
    case.activation_at = parsed.activation_at
    case.hma = parsed.hma
    case.killip = parsed.killip
    case.hgt = parsed.hgt
    case.medications_without_piam = parsed.medications_without_piam
    case.medications_with_piam = parsed.medications_with_piam
    case.ecg_description = parsed.ecg_description
    case.current_status = parsed.current_status
    # Store raw vitals as a single blob for round-tripping in the formatter.
    vitals = []
    if parsed.pa:
        vitals.append(f"PA: {parsed.pa}")
    if parsed.fc:
        vitals.append(f"FC: {parsed.fc}")
    if parsed.fr:
        vitals.append(f"FR: {parsed.fr}")
    if parsed.sato2:
        vitals.append(f"SatO2: {parsed.sato2}")
    case.admission_exam = "; ".join(vitals) if vitals else None


def create_case_from_text(
    session: Session,
    raw_text: str,
    *,
    source_chat_id: str | None = None,
    actor_id: str | None = None,
) -> Case:
    """Parse text, persist a new case with a fresh public_id, and audit it."""
    parsed = parse_case(raw_text)
    case = Case(
        public_id=generate_public_id(session),
        status="novo",
        source_chat_id=source_chat_id,
        raw_input=raw_text,
    )
    _apply_parsed(case, parsed)
    case.piam_formatted_text = format_from_parsed(parsed)
    session.add(case)
    session.flush()  # assign id without full commit
    audit.record(
        session,
        action="case.created",
        actor_type="bot" if actor_id else "system",
        actor_id=actor_id,
        case_id=case.id,
        payload={"public_id": case.public_id, "source": "telegram_text"},
        commit=False,
    )
    session.commit()
    return case


def find_open_case_for_chat(session: Session, chat_id: str) -> Case | None:
    """Most recent open case for a given chat (for attaching follow-ups/files)."""
    stmt = (
        select(Case)
        .where(Case.source_chat_id == str(chat_id))
        .where(Case.status.in_(OPEN_STATUSES))
        .order_by(Case.created_at.desc())
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none()


def record_message(
    session: Session,
    *,
    telegram_message_id: str | None,
    telegram_chat_id: str | None,
    telegram_user_id: str | None,
    telegram_username: str | None,
    text: str | None,
    case_id: int | None = None,
) -> TelegramMessage:
    """Persist a raw inbound Telegram message for full traceability."""
    msg = TelegramMessage(
        telegram_message_id=str(telegram_message_id) if telegram_message_id else None,
        telegram_chat_id=str(telegram_chat_id) if telegram_chat_id else None,
        telegram_user_id=str(telegram_user_id) if telegram_user_id else None,
        telegram_username=telegram_username,
        text=text,
        case_id=case_id,
    )
    session.add(msg)
    session.commit()
    return msg


def dashboard_link(public_id: str) -> str:
    return f"{settings.base_url.rstrip('/')}/cases/{public_id}"
