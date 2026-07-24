from __future__ import annotations

from typing import Protocol


class WebContentPort(Protocol):
    """Fetches the text content of a URL (e.g. a job posting page)."""

    def fetch(self, url: str) -> str: ...
