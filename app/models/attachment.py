"""Attachment model — files received via Telegram, stored with metadata."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, TimestampMixin

ATTACHMENT_TYPES = ("ecg_image", "ecg_pdf", "clinical_document", "other")


class Attachment(TimestampMixin, Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cases.id"), nullable=True)
    telegram_file_id: Mapped[Optional[str]] = mapped_column(String(255))
    file_name: Mapped[Optional[str]] = mapped_column(String(512))
    mime_type: Mapped[Optional[str]] = mapped_column(String(128))
    storage_path: Mapped[Optional[str]] = mapped_column(String(1024))
    attachment_type: Mapped[str] = mapped_column(String(32), default="other")

    case = relationship("Case", back_populates="attachments")
    interpretations = relationship("EcgInterpretation", back_populates="attachment")
