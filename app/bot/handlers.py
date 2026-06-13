"""Telegram bot handlers.

Security model:
- Group messages are only processed for the configured TELEGRAM_GROUP_ID.
- Private chats are only processed for the configured TELEGRAM_ADMIN_ID.
- Everything else is silently ignored.

The handlers stay thin: they translate Telegram updates into calls to the
transport-agnostic ingestion service and never make clinical judgements.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from telegram import Update
from telegram.ext import ContextTypes

from app.config import settings
from app.db import SessionLocal
from app.models.attachment import Attachment
from app.models.case import Case
from app.services import audit, file_storage, telegram_ingest
from app.services.piam_formatter import format_from_case

logger = logging.getLogger("piam.bot")

PREVIEW_LINES = 8


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------


def _is_authorized(update: Update) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    if chat is None:
        return False
    # Never react to other bots — avoids loops and spurious cases from
    # integrations posting in the group.
    if user is not None and getattr(user, "is_bot", False):
        return False
    group_id = settings.resolved_group_id
    admin_id = settings.resolved_admin_id
    if chat.type in ("group", "supergroup"):
        return group_id != "" and str(chat.id) == str(group_id)
    if chat.type == "private":
        return admin_id != "" and user is not None and str(user.id) == str(admin_id)
    return False


def _is_admin(update: Update) -> bool:
    """True only for the configured TELEGRAM_ADMIN_ID (mutating commands)."""
    admin_id = settings.resolved_admin_id
    user = update.effective_user
    return admin_id != "" and user is not None and str(user.id) == str(admin_id)


def _preview(text: str) -> str:
    lines = text.splitlines()
    head = "\n".join(lines[:PREVIEW_LINES])
    return head + ("\n…" if len(lines) > PREVIEW_LINES else "")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return
    await update.effective_message.reply_text(
        "PIAM CaseHub ativo. Envie a história clínica ou use /novo, "
        "/casos, /fechar <id>, /resumo <id>."
    )


async def cmd_novo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return
    msg = update.effective_message
    text = msg.text or ""
    # Strip the /novo command prefix to get the clinical body.
    body = text.partition(" ")[2].strip() if " " in text else ""
    chat_id = str(update.effective_chat.id)
    with SessionLocal() as session:
        case = telegram_ingest.create_case_from_text(
            session, body, source_chat_id=chat_id,
            actor_id=str(update.effective_user.id) if update.effective_user else None,
        )
        telegram_ingest.record_message(
            session,
            telegram_message_id=msg.message_id,
            telegram_chat_id=chat_id,
            telegram_user_id=update.effective_user.id if update.effective_user else None,
            telegram_username=update.effective_user.username if update.effective_user else None,
            text=text,
            case_id=case.id,
        )
        await _reply_case_created(update, case)


async def cmd_casos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return
    with SessionLocal() as session:
        rows = session.execute(
            select(Case).order_by(Case.created_at.desc()).limit(10)
        ).scalars().all()
    if not rows:
        await update.effective_message.reply_text("Nenhum caso registrado ainda.")
        return
    lines = [
        f"{c.public_id} · {c.status} · {c.patient_name or 'sem nome'}" for c in rows
    ]
    await update.effective_message.reply_text("Últimos casos:\n" + "\n".join(lines))


async def cmd_fechar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return
    # Closing a case is a mutating action — restrict it to the admin.
    if not _is_admin(update):
        await update.effective_message.reply_text(
            "Apenas o administrador pode encerrar casos."
        )
        return
    args = context.args or []
    if not args:
        await update.effective_message.reply_text("Uso: /fechar <public_id>")
        return
    public_id = args[0].strip()

    with SessionLocal() as session:
        case = session.execute(
            select(Case).where(Case.public_id == public_id)
        ).scalar_one_or_none()
        if not case:
            await update.effective_message.reply_text(f"Caso {public_id} não encontrado.")
            return
        case.status = "encerrado"
        audit.record(
            session,
            action="case.closed",
            actor_type="bot",
            actor_id=str(update.effective_user.id) if update.effective_user else None,
            case_id=case.id,
            commit=False,
        )
        session.commit()
    await update.effective_message.reply_text(f"Caso {public_id} encerrado.")


async def cmd_resumo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return
    args = context.args or []
    if not args:
        await update.effective_message.reply_text("Uso: /resumo <public_id>")
        return
    public_id = args[0].strip()
    with SessionLocal() as session:
        case = session.execute(
            select(Case).where(Case.public_id == public_id)
        ).scalar_one_or_none()
        if not case:
            await update.effective_message.reply_text(f"Caso {public_id} não encontrado.")
            return
        text = case.piam_formatted_text or format_from_case(case)
    await update.effective_message.reply_text(text)


# ---------------------------------------------------------------------------
# Free text and files
# ---------------------------------------------------------------------------


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return
    msg = update.effective_message
    text = msg.text or ""
    chat_id = str(update.effective_chat.id)
    if not text.strip():
        return

    with SessionLocal() as session:
        # Heuristic: short messages without clinical markers are treated as
        # follow-up notes attached to the most recent open case; otherwise a
        # new case is created.
        open_case = telegram_ingest.find_open_case_for_chat(session, chat_id)
        if open_case and not _looks_like_new_case(text):
            telegram_ingest.record_message(
                session,
                telegram_message_id=msg.message_id,
                telegram_chat_id=chat_id,
                telegram_user_id=update.effective_user.id if update.effective_user else None,
                telegram_username=update.effective_user.username if update.effective_user else None,
                text=text,
                case_id=open_case.id,
            )
            return
        case = telegram_ingest.create_case_from_text(
            session, text, source_chat_id=chat_id,
            actor_id=str(update.effective_user.id) if update.effective_user else None,
        )
        telegram_ingest.record_message(
            session,
            telegram_message_id=msg.message_id,
            telegram_chat_id=chat_id,
            telegram_user_id=update.effective_user.id if update.effective_user else None,
            telegram_username=update.effective_user.username if update.effective_user else None,
            text=text,
            case_id=case.id,
        )
        await _reply_case_created(update, case)


def _looks_like_new_case(text: str) -> bool:
    """Cheap heuristic: clinical narrative tends to be long / multi-field."""
    if len(text) > 200:
        return True
    markers = ("hma", "admiss", "paciente", "anos", "queixa", "pa:", "ecg")
    low = text.lower()
    return sum(1 for m in markers if m in low) >= 2


async def on_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Attach a photo/document to the most recent open case in this chat."""
    if not _is_authorized(update):
        return
    msg = update.effective_message
    chat_id = str(update.effective_chat.id)

    tg_file_id, file_name, mime_type = _extract_file_meta(msg)
    if tg_file_id is None:
        return

    with SessionLocal() as session:
        case = telegram_ingest.find_open_case_for_chat(session, chat_id)
        if case is None:
            # No open case: create a stub so the file is never lost.
            case = telegram_ingest.create_case_from_text(
                session, "", source_chat_id=chat_id,
                actor_id=str(update.effective_user.id) if update.effective_user else None,
            )

        att_type = file_storage.classify_attachment(mime_type, file_name)
        safe_name = file_storage.sanitize_filename(file_name, default=f"{tg_file_id}.bin")

        # Download bytes via Telegram and persist them.
        storage_path = None
        try:
            tg_file = await context.bot.get_file(tg_file_id)
            data = bytes(await tg_file.download_as_bytearray())
            storage_path = await file_storage.save_bytes(case.public_id, safe_name, data)
        except Exception:  # pragma: no cover - network/runtime guard
            logger.exception("Falha ao baixar anexo %s", tg_file_id)

        attachment = Attachment(
            case_id=case.id,
            telegram_file_id=tg_file_id,
            file_name=safe_name,
            mime_type=mime_type,
            storage_path=storage_path,
            attachment_type=att_type,
        )
        session.add(attachment)
        telegram_ingest.record_message(
            session,
            telegram_message_id=msg.message_id,
            telegram_chat_id=chat_id,
            telegram_user_id=update.effective_user.id if update.effective_user else None,
            telegram_username=update.effective_user.username if update.effective_user else None,
            text=msg.caption or "[arquivo]",
            case_id=case.id,
        )
        audit.record(
            session,
            action="attachment.added",
            actor_type="bot",
            actor_id=str(update.effective_user.id) if update.effective_user else None,
            case_id=case.id,
            payload={"type": att_type, "file_name": safe_name},
            commit=False,
        )
        session.commit()
        await msg.reply_text(
            f"Anexo recebido ({att_type}) e vinculado ao caso {case.public_id}."
        )


def _extract_file_meta(msg) -> tuple[str | None, str | None, str | None]:
    if msg.document is not None:
        return msg.document.file_id, msg.document.file_name, msg.document.mime_type
    if msg.photo:
        # photo is a list of sizes; take the largest.
        photo = msg.photo[-1]
        return photo.file_id, f"{photo.file_id}.jpg", "image/jpeg"
    return None, None, None


async def _reply_case_created(update: Update, case: Case) -> None:
    link = telegram_ingest.dashboard_link(case.public_id)
    preview = _preview(case.piam_formatted_text or "")
    await update.effective_message.reply_text(
        f"Caso criado: {case.public_id}\n"
        f"Status: {case.status}\n\n"
        f"Prévia PIAM:\n{preview}\n\n"
        f"Abrir no dashboard: {link}"
    )
