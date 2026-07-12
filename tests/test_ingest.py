from pathlib import Path

import pytest

from cvpal.ingest import discover_source_files, extract_one, infer_doc_kind, ingest_all

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    "filename,expected_kind",
    [
        ("cover-letter-Bruno.pdf", "cover_letter"),
        ("carta-presentacion.docx", "cover_letter"),
        ("CV-Bruno-Vargas-Tettamanti.pdf", "cv"),
        ("random-notes.odt", "cv"),
    ],
)
def test_infer_doc_kind(filename, expected_kind, tmp_path):
    path = tmp_path / filename
    assert infer_doc_kind(path) == expected_kind


def test_discover_source_files_only_supported_extensions(tmp_path):
    (tmp_path / "a.pdf").touch()
    (tmp_path / "b.docx").touch()
    (tmp_path / "c.odt").touch()
    (tmp_path / "d.txt").touch()
    (tmp_path / "Untitled Document").touch()

    found = discover_source_files(tmp_path)
    assert {p.name for p in found} == {"a.pdf", "b.docx", "c.odt"}


def test_extract_one_clean_recent_pdf():
    doc = extract_one(FIXTURES / "clean-recent.pdf", FIXTURES)
    assert doc.doc_kind == "cv"
    assert doc.source_language == "es"
    assert not doc.extraction_warnings
    assert "summary" in doc.sections
    assert "experience" in doc.sections


def test_extract_one_older_messy_pdf_still_extracts_something():
    doc = extract_one(FIXTURES / "older-messy.pdf", FIXTURES)
    assert doc.doc_kind == "cv"
    total_text = "".join(doc.sections.values()) + (doc.unstructured or "")
    assert len(total_text) > 100


def test_extract_one_docx():
    doc = extract_one(FIXTURES / "sample.docx", FIXTURES)
    assert doc.doc_kind == "cv"
    assert "experience" in doc.sections


def test_extract_one_odt():
    doc = extract_one(FIXTURES / "sample.odt", FIXTURES)
    assert doc.doc_kind == "cv"
    total_text = "".join(doc.sections.values()) + (doc.unstructured or "")
    assert len(total_text) > 100


def test_extract_one_cover_letter_has_no_sections():
    doc = extract_one(FIXTURES / "cover-letter.pdf", FIXTURES)
    assert doc.doc_kind == "cover_letter"
    assert doc.sections == {}
    assert doc.unstructured is not None
    assert len(doc.unstructured) > 50


def test_ingest_all_never_raises_on_bad_file(tmp_path):
    (tmp_path / "corrupted.pdf").write_bytes(b"not a real pdf")
    docs = ingest_all(tmp_path)
    assert len(docs) == 1
    assert docs[0].extraction_warnings
