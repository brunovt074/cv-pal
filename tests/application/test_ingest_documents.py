from cvpal.application.use_cases.ingest_documents import ingest_documents
from cvpal.infrastructure.parsers.dispatch import MultiFormatDocumentParser


def test_ingest_documents_never_raises_on_bad_file(tmp_path):
    (tmp_path / "corrupted.pdf").write_bytes(b"not a real pdf")
    docs = ingest_documents(tmp_path, MultiFormatDocumentParser())
    assert len(docs) == 1
    assert docs[0].extraction_warnings
