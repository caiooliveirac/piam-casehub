"""Deterministic clinical-text parser (no external AI).

Extracts structured fields from free Telegram text using regex + heuristics.
Philosophy: be conservative. When a value is not confidently found, leave it
as None so the formatter decides between an empty label and 'Não informado'.
This module never infers diagnoses or makes clinical judgements.
"""

from __future__ import annotations

import re

from app.schemas.case import ParsedCase

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _search(pattern: str, text: str, group: int = 1) -> str | None:
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return None
    value = m.group(group)
    # The capture group may not participate (e.g. an alternation matched the
    # other branch). Treat that as "not found" instead of crashing.
    if value is None:
        return None
    value = value.strip()
    return value or None


def _labelled(label: str, text: str) -> str | None:
    """Extract the value after a 'Label:' up to end of line.

    `label` is wrapped in a non-capturing group so alternations (e.g.
    "MP|médico plantonista") bind to the colon/value, not just the first branch.
    """
    pattern = rf"(?:{label})\s*:\s*(.+)"
    return _search(pattern, text)


# ---------------------------------------------------------------------------
# Field extractors
# ---------------------------------------------------------------------------


def _age(text: str) -> str | None:
    # "65 anos", "Idade: 65", "paciente de 65a"
    value = _labelled("idade", text)
    if value:
        m = re.search(r"\d{1,3}", value)
        if m:
            return f"{m.group(0)} anos"
    m = re.search(r"(\d{1,3})\s*anos", text, re.IGNORECASE)
    if m:
        return f"{m.group(1)} anos"
    return None


def _blood_pressure(text: str) -> str | None:
    # "PA: 92/55", "PA 92x55 mmHg"
    m = re.search(
        r"\bPA\b\s*:?\s*(\d{2,3})\s*[/x]\s*(\d{2,3})\s*(mmHg)?",
        text,
        re.IGNORECASE,
    )
    if m:
        return f"{m.group(1)}/{m.group(2)} mmHg"
    return None


def _heart_rate(text: str) -> str | None:
    m = re.search(r"\bFC\b\s*:?\s*(\d{2,3})\s*(bpm)?", text, re.IGNORECASE)
    if m:
        return f"{m.group(1)} bpm"
    return None


def _resp_rate(text: str) -> str | None:
    m = re.search(r"\bFR\b\s*:?\s*(\d{1,2})\s*(irpm|rpm)?", text, re.IGNORECASE)
    if m:
        return f"{m.group(1)} irpm"
    return None


def _sato2(text: str) -> str | None:
    m = re.search(r"(?:SatO2|SpO2|Sat\.?\s*O2|saturação)\s*:?\s*(\d{2,3})\s*%?",
                  text, re.IGNORECASE)
    if m:
        return f"{m.group(1)}%"
    return None


def _killip(text: str) -> str | None:
    # "Killip II", "Killip: 2", "Killip 1"
    m = re.search(r"Killip\s*:?\s*(IV|III|II|I|[1-4])\b", text, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return None


def _hgt(text: str) -> str | None:
    m = re.search(r"\bHGT\b\s*:?\s*(\d{2,3})\s*(mg/dl)?", text, re.IGNORECASE)
    if m:
        return m.group(1)
    return None


def _pain_score(text: str) -> str | None:
    # "dor 4/10", "dor torácica 7/10", "EVA 8/10"
    m = re.search(r"(?:dor|eva)\D{0,20}?(\d{1,2})\s*/\s*10", text, re.IGNORECASE)
    if m:
        return f"{m.group(1)}/10"
    return None


def _datetime_after(label: str, text: str) -> str | None:
    """Find a date/time near a label such as 'Admissão' or 'ECG'."""
    value = _labelled(label, text)
    if not value:
        return None
    # Capture dd/mm/yyyy hh:mm or just hh:mm
    m = re.search(r"(\d{2}/\d{2}/\d{2,4}\s+\d{1,2}:\d{2}|\d{1,2}:\d{2}|\d{2}/\d{2}/\d{2,4})",
                  value)
    if m:
        return m.group(1)
    return value


def _weight(text: str) -> str | None:
    value = _labelled("peso", text)
    if value:
        m = re.search(r"[\d\-–]+\s*kg", value, re.IGNORECASE)
        return m.group(0) if m else value
    m = re.search(r"(\d{2,3}(?:[-–]\d{2,3})?)\s*kg", text, re.IGNORECASE)
    return f"{m.group(1)} kg" if m else None


def _allergies(text: str) -> str | None:
    """Recognise PIAM phrasings: 'Alergias: X', 'Nega alergias', 'Alérgico a X'."""
    value = _labelled("alergias", text)
    if value:
        return value
    m = re.search(r"(nega\s+alergias|al[ée]rgic[oa][^.\n]*)", text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def _thrombolysis(text: str) -> str | None:
    """'Contraindicação a trombólise? <valor>' or 'Contraindicação ...: <valor>'."""
    m = re.search(
        r"contraindica[çc][ãa]o\s*(?:a|à)?\s*tromb[óo]lise\s*[?:]?\s*([^\n.]+)",
        text,
        re.IGNORECASE,
    )
    if m:
        v = m.group(1).strip()
        return v or None
    return None


def _covid(text: str) -> str | None:
    """'COVID: <valor>' or 'COVID <valor>' up to end of line."""
    m = re.search(r"\bCOVID\b\s*:?\s*([^\n]+)", text, re.IGNORECASE)
    return m.group(1).strip() if m and m.group(1).strip() else None


# Headers that terminate a captured section even without a blank line between.
_SECTION_STOP = (
    r"HMA",
    r"Exames da Admiss[ãa]o",
    r"Medica[çc][õo]es administradas",
    r"SEM orienta[çc][ãa]o do PIAM",
    r"COM orienta[çc][ãa]o do PIAM",
    r"ECG",
    r"No momento",
)


def _section(label: str, text: str) -> str | None:
    """Capture a multi-line block after 'Label:' until a blank line or next header."""
    stop = "|".join(rf"\n{h}\s*:" for h in _SECTION_STOP)
    pattern = rf"{label}\s*:\s*\n*(.+?)(?:\n\s*\n|{stop}|\Z)"
    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1).strip() or None
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_case(text: str) -> ParsedCase:
    """Parse free clinical text into a ParsedCase. Always returns an object."""
    text = (text or "").strip()
    if not text:
        return ParsedCase()

    parsed = ParsedCase(
        patient_name=_labelled(r"nome(?:\s+do\s+paciente)?", text),
        patient_age=_age(text),
        patient_weight=_weight(text),
        patient_birth_date=_labelled(r"(?:data\s+de\s+)?nascimento", text),
        companion=_labelled("acompanhante", text),
        health_plan=_labelled(r"plano(?:\s+de\s+saúde)?", text),
        origin_unit=_labelled(r"unidade(?:\s+de\s+origem)?", text),
        mp=_labelled(r"\bMP\b|m[ée]dico\s+plantonista", text),
        admission_at=_datetime_after(r"admiss[ãa]o", text),
        ecg_at=_datetime_after(r"ECG", text),
        activation_at=_datetime_after(r"acionamento", text),
        pa=_blood_pressure(text),
        fc=_heart_rate(text),
        fr=_resp_rate(text),
        sato2=_sato2(text),
        killip=_killip(text),
        hgt=_hgt(text),
        pain_score=_pain_score(text),
        allergies=_allergies(text),
        covid=_covid(text),
        thrombolysis_contraindication=_thrombolysis(text),
    )

    # HMA: prefer an explicit "HMA:" section, otherwise leave None.
    parsed.hma = _section("HMA", text)

    # Medications: capture blocks for the two PIAM categories when present.
    parsed.medications_without_piam = _section(
        r"SEM\s+orienta[çc][ãa]o\s+do\s+PIAM", text
    )
    parsed.medications_with_piam = _section(
        r"COM\s+orienta[çc][ãa]o\s+do\s+PIAM", text
    )

    # Current status: prefer "No momento:" block.
    parsed.current_status = _section(r"no\s+momento", text)
    if not parsed.current_status and parsed.pain_score:
        parsed.current_status = f"Paciente com dor {parsed.pain_score}"

    # ECG description fallback when only a time is known.
    if not parsed.ecg_description and parsed.ecg_at:
        parsed.ecg_description = f"Realizado às {parsed.ecg_at}"

    return parsed
