"""File-storage tests: filename sanitization and attachment classification."""

from __future__ import annotations

from app.services.file_storage import classify_attachment, sanitize_filename


def test_sanitize_strips_path_components():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("/abs/path/ecg.pdf") == "ecg.pdf"
    assert "/" not in sanitize_filename("a/b/c.png")


def test_sanitize_normalizes_unicode_and_spaces():
    out = sanitize_filename("ECG paciente João.pdf")
    assert " " not in out
    assert out.lower().endswith(".pdf")


def test_sanitize_empty_uses_default():
    assert sanitize_filename(None) == "file"
    assert sanitize_filename("", default="x.bin") == "x.bin"
    # A name made only of dangerous chars collapses to the default.
    assert sanitize_filename("///", default="fallback") == "fallback"


def test_classify_attachment():
    assert classify_attachment("image/jpeg", "x.jpg") == "ecg_image"
    assert classify_attachment("application/pdf", "ecg.pdf") == "ecg_pdf"
    assert classify_attachment(None, "scan.PDF") == "ecg_pdf"
    assert classify_attachment("text/plain", "notes.txt") == "clinical_document"
    assert classify_attachment(None, "weird.xyz") == "other"
