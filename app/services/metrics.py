"""Dashboard and research metrics.

Time-delta metrics parse the free-text timestamp fields best-effort; cases
whose timestamps cannot be parsed are simply excluded from those medians.
"""

from __future__ import annotations

import statistics
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.attachment import Attachment
from app.models.case import CASE_STATUSES, Case

_DT_FORMATS = ("%d/%m/%Y %H:%M", "%d/%m/%y %H:%M", "%H:%M")


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    for fmt in _DT_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _median_minutes(cases: list[Case], start_attr: str, end_attr: str) -> float | None:
    deltas: list[float] = []
    for c in cases:
        a = _parse_dt(getattr(c, start_attr))
        b = _parse_dt(getattr(c, end_attr))
        if a and b and b >= a:
            deltas.append((b - a).total_seconds() / 60.0)
    return round(statistics.median(deltas), 1) if deltas else None


def dashboard_metrics(session: Session) -> dict[str, Any]:
    """Headline numbers for the dashboard cards."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)

    total = session.execute(select(func.count()).select_from(Case)).scalar_one()
    today = session.execute(
        select(func.count()).select_from(Case).where(Case.created_at >= today_start)
    ).scalar_one()
    last7 = session.execute(
        select(func.count()).select_from(Case).where(Case.created_at >= week_start)
    ).scalar_one()

    by_status = {
        status: session.execute(
            select(func.count()).select_from(Case).where(Case.status == status)
        ).scalar_one()
        for status in CASE_STATUSES
    }

    without_outcome = session.execute(
        select(func.count())
        .select_from(Case)
        .where((Case.outcome.is_(None)) | (Case.outcome == ""))
    ).scalar_one()

    with_ecg = session.execute(
        select(func.count(func.distinct(Attachment.case_id))).where(
            Attachment.attachment_type.in_(("ecg_image", "ecg_pdf"))
        )
    ).scalar_one()

    all_cases = session.execute(select(Case)).scalars().all()

    return {
        "total": total,
        "today": today,
        "last7": last7,
        "by_status": by_status,
        "without_outcome": without_outcome,
        "with_ecg": with_ecg,
        "median_admission_to_ecg": _median_minutes(all_cases, "admission_at", "ecg_at"),
        "median_ecg_to_activation": _median_minutes(all_cases, "ecg_at", "activation_at"),
    }


def research_metrics(session: Session) -> dict[str, Any]:
    """Tabular metrics for the research-oriented /metrics page."""
    cases = session.execute(select(Case)).scalars().all()

    by_unit: dict[str, int] = {}
    by_destination: dict[str, int] = {}
    by_outcome: dict[str, int] = {}
    by_day: dict[str, int] = {}
    for c in cases:
        unit = (c.origin_unit or "Não informado").strip() or "Não informado"
        by_unit[unit] = by_unit.get(unit, 0) + 1
        dest = (c.destination or "Não informado").strip() or "Não informado"
        by_destination[dest] = by_destination.get(dest, 0) + 1
        out = (c.outcome or "Não informado").strip() or "Não informado"
        by_outcome[out] = by_outcome.get(out, 0) + 1
        day = c.created_at.date().isoformat() if c.created_at else "?"
        by_day[day] = by_day.get(day, 0) + 1

    by_status = {
        status: sum(1 for c in cases if c.status == status) for status in CASE_STATUSES
    }

    complete = sum(1 for c in cases if _is_complete(c))
    pct_complete = round(100 * complete / len(cases), 1) if cases else 0.0

    return {
        "total": len(cases),
        "by_day": dict(sorted(by_day.items())),
        "by_unit": dict(sorted(by_unit.items(), key=lambda kv: -kv[1])),
        "by_status": by_status,
        "by_destination": by_destination,
        "by_outcome": by_outcome,
        "pct_complete": pct_complete,
        "median_admission_to_ecg": _median_minutes(cases, "admission_at", "ecg_at"),
        "median_ecg_to_activation": _median_minutes(cases, "ecg_at", "activation_at"),
        # Activation -> PIAM orientation requires a future orientation timestamp.
        "median_activation_to_orientation": None,
    }


_CORE_FIELDS = ("patient_name", "patient_age", "origin_unit", "admission_at", "ecg_at")


def _is_complete(case: Case) -> bool:
    return all(bool(getattr(case, f)) for f in _CORE_FIELDS)


# ---------------------------------------------------------------------------
# Research export — placeholder (LGPD: anonymized output only)
# ---------------------------------------------------------------------------

# Fields safe to export without re-identifying the patient. Direct identifiers
# (name, companion, birth date, free-text narrative) are intentionally excluded.
ANONYMIZED_FIELDS = (
    "public_id",
    "status",
    "patient_age",
    "origin_unit",
    "killip",
    "admission_at",
    "ecg_at",
    "activation_at",
    "destination",
    "outcome",
)


def export_anonymized_cases(session: Session) -> list[dict[str, Any]]:
    """Return an anonymized, research-safe view of all cases.

    Placeholder for the future analytic dataset. Returns dicts (no CSV yet) so
    callers decide on serialization. Never includes direct identifiers.
    See docs/RESEARCH_SCHEMA.md for the LGPD rationale.
    """
    cases = session.execute(select(Case)).scalars().all()
    rows: list[dict[str, Any]] = []
    for c in cases:
        rows.append({f: getattr(c, f) for f in ANONYMIZED_FIELDS})
    return rows
