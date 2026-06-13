"""Telegram message model — every received message is recorded for traceability."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, TimestampMixin


class TelegramMessage(TimestampMixin, Base):
    __tablename__ = "telegram_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_message_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    telegram_chat_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    telegram_user_id: Mapped[Optional[str]] = mapped_column(String(64))
    telegram_username: Mapped[Optional[str]] = mapped_column(String(255))
    text: Mapped[Optional[str]] = mapped_column(Text)
    case_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cases.id"), nullable=True)

    case = relationship("Case", back_populates="messages")
