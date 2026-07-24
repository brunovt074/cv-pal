import os
import time

from cvpal.domain.documents.models import RawDocument
from cvpal.infrastructure.persistence.cv_version_inventory import build_cv_versions, infer_stack


def test_infer_stack_uses_top_level_folder():
    assert infer_stack("Java/foo.pdf") == "Java"
    assert infer_stack("generic/bar.docx") == "generic"


def test_infer_stack_root_file_has_no_stack_folder():
    assert infer_stack("foo.pdf") == "root"


def test_build_cv_versions_flags_most_recent_per_stack(tmp_path):
    (tmp_path / "Java").mkdir()
    older = tmp_path / "Java" / "old.pdf"
    newer = tmp_path / "Java" / "new.pdf"
    older.write_text("x")
    time.sleep(0.01)
    newer.write_text("x")
    os.utime(older, (time.time() - 100, time.time() - 100))

    docs = [
        RawDocument(source_file="Java/old.pdf", doc_kind="cv", source_language="en"),
        RawDocument(source_file="Java/new.pdf", doc_kind="cv", source_language="en"),
    ]
    entries = build_cv_versions(docs, tmp_path)
    by_file = {e.source_file: e for e in entries}

    assert by_file["Java/old.pdf"].is_most_recent_variant is False
    assert by_file["Java/new.pdf"].is_most_recent_variant is True


def test_build_cv_versions_ignores_cover_letters(tmp_path):
    (tmp_path / "a.pdf").write_text("x")
    docs = [
        RawDocument(source_file="a.pdf", doc_kind="cv", source_language="en"),
        RawDocument(source_file="b.pdf", doc_kind="cover_letter", source_language="en"),
    ]
    entries = build_cv_versions(docs, tmp_path)
    assert len(entries) == 1
    assert entries[0].source_file == "a.pdf"
