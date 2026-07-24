from __future__ import annotations

from typing import Protocol

from cvpal.domain.jobs.models import JobPosting


class JobPostingSourcePort(Protocol):
    """Obtains a job posting's text, regardless of how it arrived —
    stdin/CLI argument, a local file (.txt/.md/.docx), or a URL.
    """

    def read(self) -> JobPosting: ...
