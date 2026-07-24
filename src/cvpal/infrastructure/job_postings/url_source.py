"""Fetches a job posting from a URL via WebContentPort.

No adapter implements WebContentPort yet - opencode's non-interactive
`run` mode auto-denies its webfetch tool's permission (see
infrastructure/agents/cli/opencode.py), and the Anthropic SDK adapter for
Fase 4 hasn't been built. Rather than fake it, this raises
CapabilityNotSupportedError until a real adapter is registered - see
AGENTS.md Decision Log.
"""

from __future__ import annotations

from cvpal.domain.capabilities import Capability
from cvpal.domain.errors import CapabilityNotSupportedError
from cvpal.domain.jobs.models import JobPosting
from cvpal.domain.ports.web_content import WebContentPort


class UrlJobPostingSource:
    def __init__(self, url: str, web_content: WebContentPort | None) -> None:
        self._url = url
        self._web_content = web_content

    def read(self) -> JobPosting:
        if self._web_content is None:
            raise CapabilityNotSupportedError("none", Capability.WEB_CONTENT)
        text = self._web_content.fetch(self._url)
        return JobPosting(source=self._url, raw_text=text.strip())
