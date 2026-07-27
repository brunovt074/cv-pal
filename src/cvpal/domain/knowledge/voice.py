from __future__ import annotations

from pydantic import BaseModel, Field


class VoiceProfile(BaseModel):
    """Style guide extracted from existing cover letters — see
    skills/voice-style/SKILL.md. Guides generation so tailored CVs and
    cover letters sound authentically like the author, in any language.
    """

    opening_style: str = ""
    closing_style: str = ""
    sentence_rhythm: str = ""
    recurring_phrases: list[str] = Field(default_factory=list)
    avoided_patterns: str = ""
    language_specific_traits: str = ""
    tone_summary: list[str] = Field(default_factory=list)
