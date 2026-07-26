from cvpal.application.use_cases.tailor_cv import tailor_cv
from cvpal.domain.generation.models import DocumentFormat
from cvpal.domain.jobs.models import JobPosting
from tests.fakes.fake_text_agent import FakeTextAgent


class _FakeJobPostingSource:
    def __init__(self, posting: JobPosting) -> None:
        self._posting = posting

    def read(self) -> JobPosting:
        return self._posting


def test_tailor_cv_defaults_to_english():
    posting = JobPosting(source="text", raw_text="Backend developer, Java, Spring Boot, remote.")
    agent = FakeTextAgent(["# CV\n\nTailored content"])

    doc = tailor_cv(
        _FakeJobPostingSource(posting),
        "## Personal Data\n...",
        agent,
    )

    assert doc.kind == "cv"
    assert doc.language == "en"
    assert doc.document_format == DocumentFormat.MARKDOWN
    assert doc.content == "# CV\n\nTailored content"


def test_tailor_cv_language_override_wins_over_default():
    posting = JobPosting(source="text", raw_text="Some posting")
    agent = FakeTextAgent(["content"])

    doc = tailor_cv(
        _FakeJobPostingSource(posting),
        "kb",
        agent,
        language_override="es",
    )
    assert doc.language == "es"


def test_tailor_cv_sends_job_posting_and_knowledge_base_in_prompt():
    posting = JobPosting(source="text", raw_text="UNIQUE_JOB_MARKER")
    agent = FakeTextAgent(["content"])

    tailor_cv(
        _FakeJobPostingSource(posting),
        "UNIQUE_KB_MARKER",
        agent,
    )

    sent_prompt = agent.requests[0].prompt
    assert "UNIQUE_JOB_MARKER" in sent_prompt
    assert "UNIQUE_KB_MARKER" in sent_prompt
