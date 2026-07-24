from __future__ import annotations

import logging
from pathlib import Path

from cvpal.domain.documents.models import RawDocument
from cvpal.domain.ports.document_parser import DocumentParserPort

logger = logging.getLogger(__name__)


def ingest_documents(root: Path, parser: DocumentParserPort) -> list[RawDocument]:
    """Parse every supported source file under `root` into a RawDocument.

    A single bad file must not abort the run - it's recorded as a document
    with an extraction_warnings entry instead of raising.
    """
    documents: list[RawDocument] = []
    for path in parser.discover(root):
        try:
            doc = parser.extract(path, root)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to extract %s: %s", path, exc)
            documents.append(
                RawDocument(
                    source_file=str(path.relative_to(root)),
                    doc_kind=parser.infer_doc_kind(path),
                    extraction_warnings=[f"Extraction failed: {exc}"],
                )
            )
            continue
        if doc.extraction_warnings:
            for warning in doc.extraction_warnings:
                logger.warning("%s: %s", doc.source_file, warning)
        documents.append(doc)
    return documents
