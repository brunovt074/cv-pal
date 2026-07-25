import shutil

import pytest
from docx import Document

from cvpal.domain.errors import DocumentRenderError
from cvpal.domain.generation.models import DocumentFormat
from cvpal.infrastructure.rendering.local_document_renderer import (
    LocalDocumentRenderer,
    markdown_to_docx,
)

_SAMPLE_MARKDOWN = """\
# Bruno Vargas Tettamanti

## Summary

Backend developer with **Java** and Spring Boot experience.

## Experience

### Acme — Developer

- Built REST APIs
- Led a **migration** project
"""

_SOFFICE_AVAILABLE = shutil.which("soffice") is not None


def test_markdown_to_docx_maps_headings():
    document = markdown_to_docx(_SAMPLE_MARKDOWN)
    headings = [p.text for p in document.paragraphs if p.style.name.startswith("Heading")]
    assert "Bruno Vargas Tettamanti" in headings
    assert "Summary" in headings
    assert "Experience" in headings
    assert "Acme — Developer" in headings


def test_markdown_to_docx_keeps_bullet_content():
    document = markdown_to_docx(_SAMPLE_MARKDOWN)
    bullets = [p.text for p in document.paragraphs if p.style.name == "List Bullet"]
    assert "Built REST APIs" in bullets
    assert any("migration" in b for b in bullets)


def test_markdown_to_docx_marks_bold_runs():
    document = markdown_to_docx("Backend developer with **Java** experience.")
    paragraph = document.paragraphs[0]
    bold_runs = [r for r in paragraph.runs if r.bold]
    assert any(r.text == "Java" for r in bold_runs)


def test_render_markdown_format_writes_content_as_is(tmp_path):
    renderer = LocalDocumentRenderer()
    output = tmp_path / "cv.md"
    result = renderer.render(_SAMPLE_MARKDOWN, document_format=DocumentFormat.MARKDOWN, output_path=output)
    assert result == output
    assert output.read_text() == _SAMPLE_MARKDOWN


def test_render_docx_format_produces_openable_document(tmp_path):
    renderer = LocalDocumentRenderer()
    output = tmp_path / "cv.docx"
    result = renderer.render(_SAMPLE_MARKDOWN, document_format=DocumentFormat.DOCX, output_path=output)
    assert result == output
    assert output.exists()
    reopened = Document(str(output))
    assert any("Bruno Vargas Tettamanti" in p.text for p in reopened.paragraphs)


@pytest.mark.skipif(not _SOFFICE_AVAILABLE, reason="soffice not installed")
def test_render_pdf_format_produces_a_real_pdf(tmp_path):
    renderer = LocalDocumentRenderer()
    output = tmp_path / "cv.pdf"
    result = renderer.render(_SAMPLE_MARKDOWN, document_format=DocumentFormat.PDF, output_path=output)
    assert result == output
    assert output.exists()
    assert output.stat().st_size > 0
    assert output.read_bytes()[:4] == b"%PDF"


def test_render_unsupported_format_raises(tmp_path):
    renderer = LocalDocumentRenderer()
    with pytest.raises(DocumentRenderError):
        renderer.render("x", document_format="not-a-format", output_path=tmp_path / "x")
