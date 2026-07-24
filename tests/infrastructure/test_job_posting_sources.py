import pytest

from cvpal.domain.capabilities import Capability
from cvpal.domain.errors import CapabilityNotSupportedError
from cvpal.infrastructure.job_postings.file_source import FileJobPostingSource
from cvpal.infrastructure.job_postings.text_source import InlineTextJobPostingSource
from cvpal.infrastructure.job_postings.url_source import UrlJobPostingSource


def test_inline_text_source_strips_whitespace():
    posting = InlineTextJobPostingSource("  some posting text  \n").read()
    assert posting.raw_text == "some posting text"
    assert posting.source == "text"


def test_file_source_reads_txt(tmp_path):
    path = tmp_path / "posting.txt"
    path.write_text("Backend developer wanted")
    posting = FileJobPostingSource(path).read()
    assert posting.raw_text == "Backend developer wanted"
    assert posting.source == str(path)


def test_file_source_reads_md(tmp_path):
    path = tmp_path / "posting.md"
    path.write_text("# Role\nBackend developer")
    posting = FileJobPostingSource(path).read()
    assert "Backend developer" in posting.raw_text


def test_file_source_rejects_unsupported_extension(tmp_path):
    path = tmp_path / "posting.pdf"
    path.write_text("x")
    with pytest.raises(ValueError, match="Unsupported"):
        FileJobPostingSource(path).read()


def test_url_source_raises_when_no_web_content_port_wired():
    source = UrlJobPostingSource("https://example.com/job", web_content=None)
    with pytest.raises(CapabilityNotSupportedError) as exc_info:
        source.read()
    assert exc_info.value.capability == Capability.WEB_CONTENT


def test_url_source_uses_web_content_port_when_available():
    class _FakeWebContent:
        def fetch(self, url: str) -> str:
            assert url == "https://example.com/job"
            return "  posting body  "

    source = UrlJobPostingSource("https://example.com/job", web_content=_FakeWebContent())
    posting = source.read()
    assert posting.raw_text == "posting body"
