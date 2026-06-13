"""Formatter tests — required sections preserved; filling rules respected."""

from __future__ import annotations

from app.services.case_parser import parse_case
from app.services.piam_formatter import (
    REQUIRED_SECTIONS,
    format_from_fields,
    format_from_parsed,
)


def test_all_required_sections_present_when_empty():
    text = format_from_fields()
    for section in REQUIRED_SECTIONS:
        assert section in text, f"seção ausente: {section}"


def test_identification_field_empty_when_absent():
    text = format_from_fields()
    # Identification fields render the label with no value (template space kept).
    assert "Nome do paciente: \n" in text
    assert "Acompanhante: \n" in text


def test_hma_block_not_fabricated_when_absent():
    text = format_from_fields()
    # HMA section exists but body is empty (no invented content).
    assert "HMA:\n\n\n" in text


def test_roundtrip_from_parsed_keeps_values():
    parsed = parse_case(
        "Nome do paciente: Maria\nIdade: 70 anos\nPA: 120/80 mmHg\nFC: 70 bpm\n"
    )
    text = format_from_parsed(parsed)
    assert "Nome do paciente: Maria" in text
    assert "Idade: 70 anos" in text
    assert "PA: 120/80 mmHg;" in text
    assert "FC: 70 bpm;" in text


def test_section_order_is_stable():
    text = format_from_fields(patient_name="X")
    assert text.index("Nome do paciente:") < text.index("HMA:")
    assert text.index("HMA:") < text.index("Exames da Admissão:")
    assert text.index("Exames da Admissão:") < text.index("Medicações administradas:")
    assert text.index("Medicações administradas:") < text.index("No momento:")
