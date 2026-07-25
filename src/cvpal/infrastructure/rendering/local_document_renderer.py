"""Local DocumentRenderPort implementation - no agent, no API key needed.

`python-docx` (already a dependency) converts markdown straight to
`.docx`; `.pdf` goes through a temporary `.docx` plus `soffice --headless
--convert-to pdf` (LibreOffice is already installed on this machine - the
project previously assumed Anthropic Agent Skills were required for
document generation, which was never actually true here; see AGENTS.md
Decision Log).
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from docx import Document

from cvpal.domain.errors import DocumentRenderError
from cvpal.domain.generation.models import DocumentFormat

_SOFFICE_TIMEOUT_SECONDS = 60
_BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")


def _add_markdown_paragraph(document: Document, text: str, style: str | None = None) -> None:
    paragraph = document.add_paragraph(style=style)
    pos = 0
    for match in _BOLD_PATTERN.finditer(text):
        if match.start() > pos:
            paragraph.add_run(text[pos : match.start()])
        bold_run = paragraph.add_run(match.group(1))
        bold_run.bold = True
        pos = match.end()
    if pos < len(text):
        paragraph.add_run(text[pos:])


def markdown_to_docx(markdown: str) -> Document:
    """Covers the markdown shape the tailoring/cv_pal prompts actually
    produce: headings, bold, bullets, plain paragraphs. Not a general
    markdown renderer - an agent that wants something this doesn't cover
    can ask for the markdown format instead.
    """
    document = Document()
    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        if line.startswith("### "):
            document.add_heading(line[4:].strip(), level=3)
        elif line.startswith("## "):
            document.add_heading(line[3:].strip(), level=2)
        elif line.startswith("# "):
            document.add_heading(line[2:].strip(), level=1)
        elif line.lstrip().startswith(("- ", "* ")):
            content = line.lstrip()[2:].strip()
            _add_markdown_paragraph(document, content, style="List Bullet")
        else:
            _add_markdown_paragraph(document, line)
    return document


class LocalDocumentRenderer:
    def render(self, content: str, *, document_format: DocumentFormat, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if document_format == DocumentFormat.MARKDOWN:
            output_path.write_text(content)
            return output_path
        if document_format == DocumentFormat.DOCX:
            markdown_to_docx(content).save(output_path)
            return output_path
        if document_format == DocumentFormat.PDF:
            return self._render_pdf(content, output_path)
        raise DocumentRenderError(f"Unsupported document format: {document_format}")

    def _render_pdf(self, content: str, output_path: Path) -> Path:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            docx_path = tmp_path / "source.docx"
            markdown_to_docx(content).save(docx_path)

            profile_dir = tmp_path / "soffice-profile"
            try:
                result = subprocess.run(
                    [
                        "soffice",
                        "--headless",
                        f"-env:UserInstallation=file://{profile_dir}",
                        "--convert-to",
                        "pdf",
                        "--outdir",
                        str(tmp_path),
                        str(docx_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=_SOFFICE_TIMEOUT_SECONDS,
                )
            except subprocess.TimeoutExpired as exc:
                raise DocumentRenderError(
                    f"soffice timed out after {_SOFFICE_TIMEOUT_SECONDS}s converting to pdf"
                ) from exc
            except FileNotFoundError as exc:
                raise DocumentRenderError("soffice binary not found - is LibreOffice installed?") from exc

            if result.returncode != 0:
                raise DocumentRenderError(f"soffice failed converting to pdf: {result.stderr[:2000]}")

            produced = tmp_path / "source.pdf"
            if not produced.exists():
                raise DocumentRenderError("soffice did not produce a PDF output")

            output_path.write_bytes(produced.read_bytes())
            return output_path
