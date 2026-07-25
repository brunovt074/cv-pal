import time

from cvpal.application.use_cases.ingest_documents import ingest_documents
from cvpal.infrastructure.parsers.dispatch import MultiFormatDocumentParser


def test_ingest_documents_never_raises_on_bad_file(tmp_path):
    (tmp_path / "corrupted.pdf").write_bytes(b"not a real pdf")
    result = ingest_documents(tmp_path, MultiFormatDocumentParser())
    assert len(result.documents) == 1
    assert result.documents[0].extraction_warnings
    assert result.reparsed_count == 1
    assert result.reused_count == 0


def test_ingest_documents_records_mtime_and_size(tmp_path):
    path = tmp_path / "corrupted.pdf"
    path.write_bytes(b"not a real pdf")
    result = ingest_documents(tmp_path, MultiFormatDocumentParser())
    doc = result.documents[0]
    assert doc.source_size == path.stat().st_size
    assert doc.source_mtime == path.stat().st_mtime


def test_ingest_documents_reuses_unchanged_file_without_reparsing(tmp_path):
    path = tmp_path / "corrupted.pdf"
    path.write_bytes(b"not a real pdf")
    first = ingest_documents(tmp_path, MultiFormatDocumentParser())

    second = ingest_documents(tmp_path, MultiFormatDocumentParser(), previous=first.documents)

    assert second.reused_count == 1
    assert second.reparsed_count == 0
    assert second.documents == first.documents


def test_ingest_documents_reparses_a_changed_file(tmp_path):
    path = tmp_path / "corrupted.pdf"
    path.write_bytes(b"not a real pdf")
    first = ingest_documents(tmp_path, MultiFormatDocumentParser())

    time.sleep(0.01)
    path.write_bytes(b"different content, still not a real pdf")

    second = ingest_documents(tmp_path, MultiFormatDocumentParser(), previous=first.documents)

    assert second.reused_count == 0
    assert second.reparsed_count == 1


def test_ingest_documents_reuses_unaffected_files_when_one_changes(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"not a real pdf a")
    (tmp_path / "b.pdf").write_bytes(b"not a real pdf b")
    first = ingest_documents(tmp_path, MultiFormatDocumentParser())

    time.sleep(0.01)
    (tmp_path / "a.pdf").write_bytes(b"changed content for a")

    second = ingest_documents(tmp_path, MultiFormatDocumentParser(), previous=first.documents)

    assert second.reused_count == 1
    assert second.reparsed_count == 1
