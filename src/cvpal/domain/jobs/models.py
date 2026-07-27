from __future__ import annotations

from pydantic import BaseModel


class JobPosting(BaseModel):
    """A job posting to tailor a CV against, however it was obtained."""

    source: str
    raw_text: str
    detected_language: str = "unknown"
