from __future__ import annotations

import logging
from pathlib import Path

from cvpal.ingest.docx_extractor import extract_docx_text
from cvpal.ingest.models import RawDocument
from cvpal.ingest.odt_extractor import extract_odt_text
from cvpal.ingest.pdf_extractor import extract_pdf_text
from cvpal.ingest.sections import detect_language, split_into_sections

logger = logging.getLogger(__name__)

_SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".odt"}

_COVER_LETTER_MARKERS = ("cover-letter", "cover_letter", "coverletter", "carta-presentacion")


def infer_doc_kind(path: Path) -> str:
    name = path.stem.lower().replace(" ", "-")
    if any(marker in name for marker in _COVER_LETTER_MARKERS):
        return "cover_letter"
    return "cv"


def discover_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if ".git" in path.parts:
            continue
        if path.suffix.lower() in _SUPPORTED_EXTENSIONS:
            files.append(path)
    return files


def extract_one(path: Path, root: Path) -> RawDocument:
    source_file = str(path.relative_to(root))
    doc_kind = infer_doc_kind(path)
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
        # Cover letters are free-form prose - no section splitting, the whole
        # text is the content. Section detection would just misfire on them.
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


def ingest_all(root: Path) -> list[RawDocument]:
    documents: list[RawDocument] = []
    for path in discover_source_files(root):
        try:
            doc = extract_one(path, root)
        except Exception as exc:  # noqa: BLE001 - a single bad file must not abort the run
            logger.warning("Failed to extract %s: %s", path, exc)
            documents.append(
                RawDocument(
                    source_file=str(path.relative_to(root)),
                    doc_kind=infer_doc_kind(path),
                    extraction_warnings=[f"Extraction failed: {exc}"],
                )
            )
            continue
        if doc.extraction_warnings:
            for warning in doc.extraction_warnings:
                logger.warning("%s: %s", doc.source_file, warning)
        documents.append(doc)
    return documents
