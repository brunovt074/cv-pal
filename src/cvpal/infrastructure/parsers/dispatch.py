"""DocumentParserPort implementation dispatching by file extension.

Discovery + per-format extraction used to live directly in
`cvpal.ingest`; the orchestration (loop, warning aggregation, one-bad-file-
doesn't-abort-the-run) moved to
`application/use_cases/ingest_documents.py`, which depends only on
DocumentParserPort - this module is the concrete implementation wired in
by container.py.
"""

from __future__ import annotations

from pathlib import Path

from cvpal.domain.documents.models import RawDocument
from cvpal.infrastructure.parsers.docx_extractor import extract_docx_text
from cvpal.infrastructure.parsers.odt_extractor import extract_odt_text
from cvpal.infrastructure.parsers.pdf_extractor import extract_pdf_text
from cvpal.infrastructure.parsers.sections import detect_language, split_into_sections

_SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".odt"}
_COVER_LETTER_MARKERS = ("cover-letter", "cover_letter", "coverletter", "carta-presentacion")


class MultiFormatDocumentParser:
    def discover(self, root: Path) -> list[Path]:
        files: list[Path] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if ".git" in path.parts:
                continue
            if path.suffix.lower() in _SUPPORTED_EXTENSIONS:
                files.append(path)
        return files

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() in _SUPPORTED_EXTENSIONS

    def infer_doc_kind(self, path: Path) -> str:
        name = path.stem.lower().replace(" ", "-")
        if any(marker in name for marker in _COVER_LETTER_MARKERS):
            return "cover_letter"
        return "cv"

    def extract(self, path: Path, root: Path) -> RawDocument:
        source_file = str(path.relative_to(root))
        doc_kind = self.infer_doc_kind(path)
        warnings: list[str] = []

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            text, pdf_warnings = extract_pdf_text(path)
            warnings.extend(pdf_warnings)
        elif suffix == ".docx":
            text = extract_docx_text(path)
        elif suffix == ".odt":
            text = extract_odt_text(path)
        else:
            raise ValueError(f"Unsupported extension: {suffix}")

        if not text.strip():
            warnings.append("Extracted text is empty")

        language = detect_language(text)

        if doc_kind == "cover_letter":
            # Cover letters are free-form prose - no section splitting, the
            # whole text is the content. Section detection would just
            # misfire on them.
            sections: dict[str, str] = {}
            unstructured: str | None = text
        else:
            sections = split_into_sections(text)
            unstructured = sections.pop("unstructured", None)
            if not sections and unstructured is None:
                unstructured = text

        return RawDocument(
            source_file=source_file,
            source_language=language,
            doc_kind=doc_kind,
            sections=sections,
            unstructured=unstructured,
            extraction_warnings=warnings,
        )
