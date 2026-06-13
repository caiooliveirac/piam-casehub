"""Web routes: health, auth, dashboard, cases, metrics.

Server-rendered with Jinja2 + HTMX + Tailwind (CDN). Protected pages check the
session and redirect to /login when absent.
"""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models.attachment import Attachment
from app.models.audit import AuditLog
from app.models.case import CASE_STATUSES, Case
from app.models.message import TelegramMessage
from app.services import audit, metrics
from app.services.piam_formatter import format_from_case
from app.web import auth

router = APIRouter()

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=_TEMPLATE_DIR)


def _ctx(request: Request, **extra) -> dict:
    base = {"request": request, "app_name": settings.app_name, "user": auth.current_user(request)}
    base.update(extra)
    return base


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@router.get("/health")
def health() -> JSONResponse:
    return JSONResponse(
        {"status": "ok", "app": settings.app_name, "env": settings.app_env}
    )


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    if auth.current_user(request):
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse("login.html", _ctx(request, error=None))


@router.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if auth.authenticate(username, password):
        auth.login_session(request, username)
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(
        "login.html", _ctx(request, error="Credenciais inválidas."), status_code=401
    )


@router.get("/logout")
def logout(request: Request):
    auth.logout_session(request)
    return RedirectResponse(url="/login", status_code=303)


@router.get("/")
def index(request: Request):
    target = "/dashboard" if auth.current_user(request) else "/login"
    return RedirectResponse(url=target, status_code=303)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    if not auth.current_user(request):
        return RedirectResponse(url="/login", status_code=303)
    with SessionLocal() as session:
        data = metrics.dashboard_metrics(session)
        recent = session.execute(
            select(Case).order_by(Case.created_at.desc()).limit(10)
        ).scalars().all()
    return templates.TemplateResponse(
        "dashboard.html", _ctx(request, m=data, recent=recent)
    )


# ---------------------------------------------------------------------------
# Cases list
# ---------------------------------------------------------------------------


@router.get("/cases", response_class=HTMLResponse)
def cases_list(
    request: Request,
    q: Optional[str] = None,
    status: Optional[str] = None,
    unit: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    with_ecg: Optional[str] = None,
    no_outcome: Optional[str] = None,
):
    if not auth.current_user(request):
        return RedirectResponse(url="/login", status_code=303)

    with SessionLocal() as session:
        stmt = select(Case)
        if q:
            stmt = stmt.where(Case.patient_name.ilike(f"%{q}%"))
        if status:
            stmt = stmt.where(Case.status == status)
        if unit:
            stmt = stmt.where(Case.origin_unit.ilike(f"%{unit}%"))
        if date_from:
            parsed = _parse_date(date_from)
            if parsed:
                stmt = stmt.where(Case.created_at >= parsed)
        if date_to:
            parsed = _parse_date(date_to)
            if parsed:
                stmt = stmt.where(Case.created_at <= _end_of_day(parsed))
        if no_outcome == "on":
            stmt = stmt.where((Case.outcome.is_(None)) | (Case.outcome == ""))

        stmt = stmt.order_by(Case.created_at.desc()).limit(200)
        cases = session.execute(stmt).scalars().all()

        # Filter "with ECG" in Python using the attachments relationship.
        ecg_case_ids = set(
            session.execute(
                select(Attachment.case_id).where(
                    Attachment.attachment_type.in_(("ecg_image", "ecg_pdf"))
                )
            ).scalars().all()
        )
        if with_ecg == "on":
            cases = [c for c in cases if c.id in ecg_case_ids]

    return templates.TemplateResponse(
        "cases_list.html",
        _ctx(
            request,
            cases=cases,
            statuses=CASE_STATUSES,
            ecg_case_ids=ecg_case_ids,
            filters={
                "q": q or "",
                "status": status or "",
                "unit": unit or "",
                "date_from": date_from or "",
                "date_to": date_to or "",
                "with_ecg": with_ecg or "",
                "no_outcome": no_outcome or "",
            },
        ),
    )


# ---------------------------------------------------------------------------
# Case detail + edit
# ---------------------------------------------------------------------------


@router.get("/cases/{public_id}", response_class=HTMLResponse)
def case_detail(request: Request, public_id: str):
    if not auth.current_user(request):
        return RedirectResponse(url="/login", status_code=303)
    with SessionLocal() as session:
        case = session.execute(
            select(Case).where(Case.public_id == public_id)
        ).scalar_one_or_none()
        if not case:
            return HTMLResponse("Caso não encontrado", status_code=404)
        messages = session.execute(
            select(TelegramMessage)
            .where(TelegramMessage.case_id == case.id)
            .order_by(TelegramMessage.created_at.asc())
        ).scalars().all()
        attachments = session.execute(
            select(Attachment).where(Attachment.case_id == case.id)
        ).scalars().all()
        logs = session.execute(
            select(AuditLog)
            .where(AuditLog.case_id == case.id)
            .order_by(AuditLog.created_at.asc())
        ).scalars().all()
        piam_text = case.piam_formatted_text or format_from_case(case)
    return templates.TemplateResponse(
        "case_detail.html",
        _ctx(
            request,
            case=case,
            messages=messages,
            attachments=attachments,
            logs=logs,
            statuses=CASE_STATUSES,
            piam_text=piam_text,
        ),
    )


@router.post("/cases/{public_id}", response_class=HTMLResponse)
def case_update(
    request: Request,
    public_id: str,
    status: str = Form(""),
    destination: str = Form(""),
    outcome: str = Form(""),
    research_notes: str = Form(""),
    piam_formatted_text: str = Form(""),
):
    user = auth.current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    with SessionLocal() as session:
        case = session.execute(
            select(Case).where(Case.public_id == public_id)
        ).scalar_one_or_none()
        if not case:
            return HTMLResponse("Caso não encontrado", status_code=404)
        changes = {}
        for field, value in (
            ("status", status),
            ("destination", destination),
            ("outcome", outcome),
            ("research_notes", research_notes),
            ("piam_formatted_text", piam_formatted_text),
        ):
            value = value.strip()
            if value and getattr(case, field) != value:
                changes[field] = value
                setattr(case, field, value)
        if changes:
            audit.record(
                session,
                action="case.updated",
                actor_type="admin",
                actor_id=user,
                case_id=case.id,
                payload={"fields": list(changes.keys())},
                commit=False,
            )
        session.commit()
    return RedirectResponse(url=f"/cases/{public_id}", status_code=303)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


@router.get("/metrics", response_class=HTMLResponse)
def metrics_page(request: Request):
    if not auth.current_user(request):
        return RedirectResponse(url="/login", status_code=303)
    with SessionLocal() as session:
        data = metrics.research_metrics(session)
    return templates.TemplateResponse("metrics.html", _ctx(request, m=data))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_date(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        try:
            d = date.fromisoformat(value)
            return datetime(d.year, d.month, d.day)
        except ValueError:
            return None


def _end_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=23, minute=59, second=59)
