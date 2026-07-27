from pathlib import Path

import pytest

from cvpal.infrastructure.parsers.dispatch import MultiFormatDocumentParser

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.mark.parametrize(
    "filename,expected_kind",
    [
        ("cover-letter-Alex.pdf", "cover_letter"),
        ("carta-presentacion.docx", "cover_letter"),
        ("CV-Alex-Doe.pdf", "cv"),
        ("random-notes.odt", "cv"),
    ],
)
def test_infer_doc_kind(filename, expected_kind, tmp_path):
    parser = MultiFormatDocumentParser()
    path = tmp_path / filename
    assert parser.infer_doc_kind(path) == expected_kind


def test_discover_only_supported_extensions(tmp_path):
    (tmp_path / "a.pdf").touch()
    (tmp_path / "b.docx").touch()
    (tmp_path / "c.odt").touch()
    (tmp_path / "d.txt").touch()
    (tmp_path / "Untitled Document").touch()

    found = MultiFormatDocumentParser().discover(tmp_path)
    assert {p.name for p in found} == {"a.pdf", "b.docx", "c.odt"}


def test_extract_clean_recent_pdf():
    doc = MultiFormatDocumentParser().extract(FIXTURES / "clean-recent.pdf", FIXTURES)
    assert doc.doc_kind == "cv"
    assert doc.source_language == "es"
    assert not doc.extraction_warnings
    assert "summary" in doc.sections
    assert "experience" in doc.sections


def test_extract_older_messy_pdf_still_extracts_something():
    doc = MultiFormatDocumentParser().extract(FIXTURES / "older-messy.pdf", FIXTURES)
    assert doc.doc_kind == "cv"
    total_text = "".join(doc.sections.values()) + (doc.unstructured or "")
    assert len(total_text) > 100


def test_extract_docx():
    doc = MultiFormatDocumentParser().extract(FIXTURES / "sample.docx", FIXTURES)
    assert doc.doc_kind == "cv"
    assert "experience" in doc.sections


def test_extract_odt():
    doc = MultiFormatDocumentParser().extract(FIXTURES / "sample.odt", FIXTURES)
    assert doc.doc_kind == "cv"
    total_text = "".join(doc.sections.values()) + (doc.unstructured or "")
    assert len(total_text) > 100


def test_extract_cover_letter_has_no_sections():
    doc = MultiFormatDocumentParser().extract(FIXTURES / "cover-letter.pdf", FIXTURES)
    assert doc.doc_kind == "cover_letter"
    assert doc.sections == {}
    assert doc.unstructured is not None
    assert len(doc.unstructured) > 50
