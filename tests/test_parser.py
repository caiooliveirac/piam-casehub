"""Parser tests — verify deterministic extraction of key clinical fields."""

from __future__ import annotations

from app.services.case_parser import parse_case

# Mirrors the structure of the real PIAM reference case.
SAMPLE = """
Nome do paciente: Gilmar Queiroz Portugal
Idade: 65 anos
Peso: 60-70 kg
Data de nascimento: 20/10/1960
Unidade de origem: Hospital FABAMED - São Francisco do Conde
MP: Dra. Geisa Bulos C. Albuquerque
Admissão: 02/06/2026 22:27
ECG: 02/06/2026 22:34

Paciente masculino, 65 anos, dor torácica em aperto há algum tempo.
Nega alergias.
Contraindicação a trombólise? Não informado.
COVID: Nega sintomas gripais.

PA: 92/55 mmHg;
FC: 89 bpm;
FR: 18 irpm;
SatO2: 96%;
Killip: II;
HGT: 110;

SEM orientação do PIAM:
Tramal.
AAS 300 mg.

No momento:

Paciente com dor 4/10
"""


def test_parser_extracts_age():
    assert parse_case(SAMPLE).patient_age == "65 anos"


def test_parser_extracts_blood_pressure():
    assert parse_case(SAMPLE).pa == "92/55 mmHg"


def test_parser_extracts_heart_rate():
    assert parse_case(SAMPLE).fc == "89 bpm"


def test_parser_extracts_sato2():
    assert parse_case(SAMPLE).sato2 == "96%"


def test_parser_extracts_killip():
    assert parse_case(SAMPLE).killip == "II"


def test_parser_extracts_pain_score():
    assert parse_case(SAMPLE).pain_score == "4/10"


def test_parser_extracts_medications():
    meds = parse_case(SAMPLE).medications_without_piam or ""
    assert "AAS" in meds and "Tramal" in meds


def test_parser_extracts_admission_and_ecg_time():
    parsed = parse_case(SAMPLE)
    assert parsed.admission_at == "02/06/2026 22:27"
    assert parsed.ecg_at == "02/06/2026 22:34"


def test_parser_extracts_resp_rate_and_hgt():
    parsed = parse_case(SAMPLE)
    assert parsed.fr == "18 irpm"
    assert parsed.hgt == "110"


def test_parser_extracts_identification_fields():
    parsed = parse_case(SAMPLE)
    assert parsed.patient_name == "Gilmar Queiroz Portugal"
    assert parsed.patient_weight == "60-70 kg"
    assert parsed.patient_birth_date == "20/10/1960"
    assert "FABAMED" in (parsed.origin_unit or "")
    assert "Geisa" in (parsed.mp or "")


def test_parser_extracts_clinical_flags():
    parsed = parse_case(SAMPLE)
    assert parsed.allergies is not None
    assert parsed.covid is not None
    assert parsed.thrombolysis_contraindication is not None


def test_parser_does_not_crash_on_words_containing_mp():
    # Regression: 'tempo'/'exemplo' contain 'mp'; the MP label must not crash
    # the parser nor be mis-extracted from arbitrary prose.
    parsed = parse_case("Paciente com dor há algum tempo. Exemplo de campo clínico.")
    assert parsed.mp is None


def test_parser_handles_empty_text():
    parsed = parse_case("")
    assert parsed.patient_age is None
    assert parsed.pa is None
