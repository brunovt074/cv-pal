from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from cvpal.domain.documents.models import RawDocument
from cvpal.domain.ports.document_parser import DocumentParserPort

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestResult:
    documents: list[RawDocument]
    reused_count: int
    reparsed_count: int


def ingest_documents(
    root: Path,
    parser: DocumentParserPort,
    previous: list[RawDocument] | None = None,
) -> IngestResult:
    """Parse every supported source file under `root` into a RawDocument.

    A single bad file must not abort the run - it's recorded as a document
    with an extraction_warnings entry instead of raising.

    If `previous` is given (the prior ingest's output), a file whose mtime
    and size are unchanged reuses its previous RawDocument instead of being
    re-parsed - re-parsing PDFs/DOCX/ODT isn't free, and most runs touch
    only a handful of files.
    """
    previous_by_file = {doc.source_file: doc for doc in (previous or [])}

    documents: list[RawDocument] = []
    reused_count = 0
    reparsed_count = 0

    for path in parser.discover(root):
        source_file = str(path.relative_to(root))
        stat = path.stat()
        mtime = stat.st_mtime
        size = stat.st_size

        cached = previous_by_file.get(source_file)
        if cached is not None and cached.source_mtime == mtime and cached.source_size == size:
            documents.append(cached)
            reused_count += 1
            continue

        try:
            doc = parser.extract(path, root)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to extract %s: %s", path, exc)
            documents.append(
                RawDocument(
                    source_file=source_file,
                    doc_kind=parser.infer_doc_kind(path),
                    extraction_warnings=[f"Extraction failed: {exc}"],
                    source_mtime=mtime,
                    source_size=size,
                )
            )
            reparsed_count += 1
            continue

        doc = doc.model_copy(update={"source_mtime": mtime, "source_size": size})
        if doc.extraction_warnings:
            for warning in doc.extraction_warnings:
                logger.warning("%s: %s", doc.source_file, warning)
        documents.append(doc)
        reparsed_count += 1

    return IngestResult(documents=documents, reused_count=reused_count, reparsed_count=reparsed_count)
