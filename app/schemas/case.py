"""Pydantic schemas for case data interchange and parser output."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ParsedCase(BaseModel):
    """Structured fields extracted by the deterministic parser.

    Every field is optional; the parser leaves unknown values as None so the
    formatter can decide between an empty label and 'Não informado'.
    """

    patient_name: Optional[str] = None
    patient_age: Optional[str] = None
    patient_weight: Optional[str] = None
    patient_birth_date: Optional[str] = None
    companion: Optional[str] = None
    health_plan: Optional[str] = None

    origin_unit: Optional[str] = None
    mp: Optional[str] = None
    admission_at: Optional[str] = None
    ecg_at: Optional[str] = None
    activation_at: Optional[str] = None

    hma: Optional[str] = None

    # Vitals
    pa: Optional[str] = None
    fc: Optional[str] = None
    fr: Optional[str] = None
    sato2: Optional[str] = None
    killip: Optional[str] = None
    hgt: Optional[str] = None
    pain_score: Optional[str] = None  # dor 0-10

    medications_without_piam: Optional[str] = None
    medications_with_piam: Optional[str] = None

    ecg_description: Optional[str] = None
    current_status: Optional[str] = None

    # Free-text clinical flags surfaced by the parser
    allergies: Optional[str] = None
    thrombolysis_contraindication: Optional[str] = None
    covid: Optional[str] = None


class CaseUpdate(BaseModel):
    """Editable fields from the case detail web form."""

    status: Optional[str] = None
    destination: Optional[str] = None
    outcome: Optional[str] = None
    research_notes: Optional[str] = None
    piam_formatted_text: Optional[str] = None


class CaseSummary(BaseModel):
    public_id: str
    status: str
    patient_name: Optional[str] = None
    origin_unit: Optional[str] = None
    preview: str = Field(default="")
