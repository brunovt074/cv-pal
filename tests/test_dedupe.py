from cvpal.analytics.dedupe import dedupe_all_sections, dedupe_section_lines
from cvpal.ingest.models import RawDocument


def _doc(source_file: str, **sections: str) -> RawDocument:
    return RawDocument(source_file=source_file, doc_kind="cv", sections=sections)


def test_dedupe_collapses_identical_lines_across_documents():
    docs = [
        _doc("a.pdf", experience="- Built REST APIs in Java"),
        _doc("b.pdf", experience="- Built REST APIs in Java"),
    ]
    blocks = dedupe_section_lines(docs, "experience")
    assert len(blocks) == 1
    assert set(blocks[0].source_files) == {"a.pdf", "b.pdf"}


def test_dedupe_normalizes_whitespace_and_bullet_markers():
    docs = [
        _doc("a.pdf", experience="  •  Built   REST APIs"),
        _doc("b.pdf", experience="- Built REST APIs"),
    ]
    blocks = dedupe_section_lines(docs, "experience")
    assert len(blocks) == 1


def test_dedupe_keeps_genuinely_different_lines_separate():
    docs = [
        _doc("a.pdf", experience="- Built REST APIs"),
        _doc("b.pdf", experience="- Wrote unit tests"),
    ]
    blocks = dedupe_section_lines(docs, "experience")
    assert len(blocks) == 2


def test_dedupe_skips_documents_missing_the_section():
    docs = [_doc("a.pdf", experience="- Did a thing"), _doc("b.pdf", education="- A degree")]
    blocks = dedupe_section_lines(docs, "experience")
    assert len(blocks) == 1
    assert blocks[0].source_files == ["a.pdf"]


def test_dedupe_all_sections_returns_one_key_per_requested_section():
    docs = [_doc("a.pdf", experience="- X", skills="- Y")]
    result = dedupe_all_sections(docs, ["experience", "skills", "education"])
    assert set(result) == {"experience", "skills", "education"}
    assert result["education"] == []
