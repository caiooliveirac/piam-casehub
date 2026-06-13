"""ECG interpretation model — placeholder table for future automated/manual reads.

This table is the integration point for a future ECG interpretation engine.
The scaffold never writes AI reads; rows are created/edited by humans for now.
See docs/ECG_INTEGRATION.md for the suggested contract.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, TimestampMixin


class EcgInterpretation(TimestampMixin, Base):
    __tablename__ = "ecg_interpretations"

    id: Mapped[int] = mapped_column(primary_key=True)
    attachment_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("attachments.id"), nullable=True
    )
    case_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cases.id"), nullable=True)

    ecg_acquired_at: Mapped[Optional[str]] = mapped_column(String(64))
    machine_read: Mapped[Optional[str]] = mapped_column(Text)
    ai_read: Mapped[Optional[str]] = mapped_column(Text)
    cardiologist_final_read: Mapped[Optional[str]] = mapped_column(Text)
    stemi_suspected: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    territory: Mapped[Optional[str]] = mapped_column(String(128))
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    warnings: Mapped[Optional[str]] = mapped_column(Text)  # JSON-encoded list

    attachment = relationship("Attachment", back_populates="interpretations")
