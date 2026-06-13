"""Case model — the central clinical record."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, TimestampMixin

# Status values kept as plain strings (documented enum) for migration simplicity.
CASE_STATUSES = (
    "novo",
    "em_avaliacao",
    "orientado",
    "transferido",
    "encerrado",
    "cancelado",
)

# Statuses considered "open" for the purpose of attaching follow-up messages/files.
OPEN_STATUSES = ("novo", "em_avaliacao", "orientado")


class Case(TimestampMixin, Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="novo", index=True)

    # Telegram chat this case originated from (used to group follow-up messages).
    source_chat_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)

    # --- Patient identification ---
    patient_name: Mapped[Optional[str]] = mapped_column(String(255))
    patient_age: Mapped[Optional[str]] = mapped_column(String(64))
    patient_weight: Mapped[Optional[str]] = mapped_column(String(64))
    patient_birth_date: Mapped[Optional[str]] = mapped_column(String(64))
    companion: Mapped[Optional[str]] = mapped_column(String(255))
    health_plan: Mapped[Optional[str]] = mapped_column(String(255))

    # --- Origin / timeline ---
    origin_unit: Mapped[Optional[str]] = mapped_column(String(512))
    mp: Mapped[Optional[str]] = mapped_column(String(255))
    admission_at: Mapped[Optional[str]] = mapped_column(String(64))
    ecg_at: Mapped[Optional[str]] = mapped_column(String(64))
    activation_at: Mapped[Optional[str]] = mapped_column(String(64))

    # --- Clinical narrative ---
    hma: Mapped[Optional[str]] = mapped_column(Text)
    admission_exam: Mapped[Optional[str]] = mapped_column(Text)
    medications_without_piam: Mapped[Optional[str]] = mapped_column(Text)
    medications_with_piam: Mapped[Optional[str]] = mapped_column(Text)
    ecg_description: Mapped[Optional[str]] = mapped_column(Text)
    current_status: Mapped[Optional[str]] = mapped_column(Text)

    # --- Structured vitals ---
    killip: Mapped[Optional[str]] = mapped_column(String(32))
    hgt: Mapped[Optional[str]] = mapped_column(String(32))

    # --- Outcome / research ---
    destination: Mapped[Optional[str]] = mapped_column(String(255))
    outcome: Mapped[Optional[str]] = mapped_column(String(255))
    research_notes: Mapped[Optional[str]] = mapped_column(Text)

    # --- Provenance ---
    raw_input: Mapped[Optional[str]] = mapped_column(Text)
    piam_formatted_text: Mapped[Optional[str]] = mapped_column(Text)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    messages = relationship("TelegramMessage", back_populates="case")
    attachments = relationship("Attachment", back_populates="case")
    audit_logs = relationship("AuditLog", back_populates="case")

    @property
    def is_open(self) -> bool:
        return self.status in OPEN_STATUSES
