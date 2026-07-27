"""Fetches a job posting page's readable text over HTTP - no agent needed,
the same deterministic-local philosophy as document rendering (see
AGENTS.md Decision Log). Strips <script>/<style>/<head> and every other
tag, collapses whitespace; not a general-purpose readability extractor,
just enough text for a tailoring prompt to work with.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from html.parser import HTMLParser

from cvpal.domain.errors import JobPostingFetchError

_TIMEOUT_SECONDS = 15
_SKIPPED_TAGS = {"script", "style", "head", "noscript", "svg"}
_USER_AGENT = "cvpal/0.1 (+job-posting-fetch)"
_BLANK_LINES = re.compile(r"\n{3,}")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self.chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in _SKIPPED_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIPPED_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data.strip():
            self.chunks.append(data.strip())


def _html_to_text(html: str) -> str:
    extractor = _TextExtractor()
    extractor.feed(html)
    return _BLANK_LINES.sub("\n\n", "\n".join(extractor.chunks)).strip()


class HttpWebContent:
    def fetch(self, url: str) -> str:
        request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                html = response.read().decode(charset, errors="replace")
        except (urllib.error.URLError, TimeoutError) as exc:
            raise JobPostingFetchError(url, str(exc)) from exc

        text = _html_to_text(html)
        if not text:
            raise JobPostingFetchError(url, "no readable text extracted from the page")
        return text
