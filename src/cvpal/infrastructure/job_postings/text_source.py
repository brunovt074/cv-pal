from __future__ import annotations

from cvpal.domain.jobs.models import JobPosting


class InlineTextJobPostingSource:
    """A job posting supplied directly as text - CLI argument or stdin."""

    def __init__(self, text: str) -> None:
        self._text = text

    def read(self) -> JobPosting:
        return JobPosting(source="text", raw_text=self._text.strip())
