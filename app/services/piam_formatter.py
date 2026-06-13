"""PIAM text formatter.

Produces the canonical PIAM textual format from structured case data, keeping
exact line/section layout. Two filling rules:
- identification fields: empty after the colon when absent;
- important clinical fields: 'Não informado' when absent.
Never invents clinical information.
"""

from __future__ import annotations

from app.models.case import Case
from app.schemas.case import ParsedCase

NOT_INFORMED = "Não informado"

# Required section markers — used by tests to assert structure is preserved.
REQUIRED_SECTIONS = (
    "Nome do paciente:",
    "Idade:",
    "Acompanhante:",
    "Plano de saúde:",
    "Unidade de origem:",
    "HMA:",
    "Exames da Admissão:",
    "PA:",
    "FC:",
    "Killip:",
    "Medicações administradas:",
    "SEM orientação do PIAM:",
    "COM orientação do PIAM:",
    "ECG:",
    "No momento:",
)


def _ident(value: str | None) -> str:
    """Identification field: empty string when absent."""
    return value.strip() if value and value.strip() else ""


def _clinical(value: str | None) -> str:
    """Important clinical field: 'Não informado' when absent."""
    return value.strip() if value and value.strip() else NOT_INFORMED


def _raw(value: str | None) -> str:
    """Free-text block: empty when absent (no fabrication)."""
    return value.strip() if value and value.strip() else ""


def format_from_fields(
    *,
    patient_name: str | None = None,
    patient_age: str | None = None,
    patient_weight: str | None = None,
    patient_birth_date: str | None = None,
    companion: str | None = None,
    health_plan: str | None = None,
    origin_unit: str | None = None,
    mp: str | None = None,
    admission_at: str | None = None,
    ecg_at: str | None = None,
    activation_at: str | None = None,
    hma: str | None = None,
    pa: str | None = None,
    fc: str | None = None,
    fr: str | None = None,
    sato2: str | None = None,
    killip: str | None = None,
    hgt: str | None = None,
    medications_without_piam: str | None = None,
    medications_with_piam: str | None = None,
    ecg_description: str | None = None,
    current_status: str | None = None,
) -> str:
    """Render the canonical PIAM text. Pure function, easy to unit test."""
    return (
        f"Nome do paciente: {_ident(patient_name)}\n"
        f"Idade: {_ident(patient_age)}\n"
        f"Peso: {_ident(patient_weight)}\n"
        f"Data de nascimento: {_ident(patient_birth_date)}\n"
        f"Acompanhante: {_ident(companion)}\n"
        f"Plano de saúde: {_ident(health_plan)}\n"
        f"\n"
        f"Unidade de origem: {_ident(origin_unit)}\n"
        f"MP: {_ident(mp)}\n"
        f"Admissão: {_ident(admission_at)}\n"
        f"ECG: {_ident(ecg_at)}\n"
        f"Acionamento: {_ident(activation_at)}\n"
        f"\n"
        f"HMA:\n"
        f"\n"
        f"{_raw(hma)}\n"
        f"\n"
        f"Exames da Admissão:\n"
        f"\n"
        f"PA: {_ident(pa)};\n"
        f"FC: {_ident(fc)};\n"
        f"FR: {_ident(fr)};\n"
        f"SatO2: {_ident(sato2)};\n"
        f"Killip: {_ident(killip)};\n"
        f"HGT: {_ident(hgt)};\n"
        f"\n"
        f"Medicações administradas:\n"
        f"\n"
        f"SEM orientação do PIAM:\n"
        f"{_raw(medications_without_piam)}\n"
        f"\n"
        f"COM orientação do PIAM:\n"
        f"{_raw(medications_with_piam)}\n"
        f"\n"
        f"ECG:\n"
        f"{_raw(ecg_description)}\n"
        f"\n"
        f"No momento:\n"
        f"\n"
        f"{_raw(current_status)}\n"
    )


def format_from_parsed(parsed: ParsedCase) -> str:
    """Render PIAM text from a ParsedCase."""
    return format_from_fields(
        patient_name=parsed.patient_name,
        patient_age=parsed.patient_age,
        patient_weight=parsed.patient_weight,
        patient_birth_date=parsed.patient_birth_date,
        companion=parsed.companion,
        health_plan=parsed.health_plan,
        origin_unit=parsed.origin_unit,
        mp=parsed.mp,
        admission_at=parsed.admission_at,
        ecg_at=parsed.ecg_at,
        activation_at=parsed.activation_at,
        hma=parsed.hma,
        pa=parsed.pa,
        fc=parsed.fc,
        fr=parsed.fr,
        sato2=parsed.sato2,
        killip=parsed.killip,
        hgt=parsed.hgt,
        medications_without_piam=parsed.medications_without_piam,
        medications_with_piam=parsed.medications_with_piam,
        ecg_description=parsed.ecg_description,
        current_status=parsed.current_status,
    )


def format_from_case(case: Case) -> str:
    """Render PIAM text from a persisted Case row."""
    return format_from_fields(
        patient_name=case.patient_name,
        patient_age=case.patient_age,
        patient_weight=case.patient_weight,
        patient_birth_date=case.patient_birth_date,
        companion=case.companion,
        health_plan=case.health_plan,
        origin_unit=case.origin_unit,
        mp=case.mp,
        admission_at=case.admission_at,
        ecg_at=case.ecg_at,
        activation_at=case.activation_at,
        hma=case.hma,
        # Vitals are stored partly structured; admission_exam holds raw vitals text.
        pa=_extract_vital(case.admission_exam, "PA"),
        fc=_extract_vital(case.admission_exam, "FC"),
        fr=_extract_vital(case.admission_exam, "FR"),
        sato2=_extract_vital(case.admission_exam, "SatO2"),
        killip=case.killip,
        hgt=case.hgt,
        medications_without_piam=case.medications_without_piam,
        medications_with_piam=case.medications_with_piam,
        ecg_description=case.ecg_description,
        current_status=case.current_status,
    )


def _extract_vital(blob: str | None, key: str) -> str | None:
    """Pull a 'KEY: value;' fragment out of a stored vitals blob, if present."""
    if not blob:
        return None
    import re

    m = re.search(rf"{key}\s*:\s*([^;\n]+)", blob, re.IGNORECASE)
    return m.group(1).strip() if m else None
