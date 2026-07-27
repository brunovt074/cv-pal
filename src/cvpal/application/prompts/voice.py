"""Prompt for extracting a VoiceProfile from cover letters - see
skills/voice-style/SKILL.md and domain/knowledge/voice.py.
"""

from __future__ import annotations

from cvpal.domain.documents.models import RawDocument

PROMPT_VERSION = "v1"
"""See application/prompts/extraction.py:PROMPT_VERSION."""


def voice_profile_prompt(letters: list[RawDocument]) -> str:
    parts = []
    for doc in letters:
        content = doc.unstructured or ""
        parts.append(f"--- {doc.source_file} [{doc.source_language}] ---\n{content[:2500]}")
    text = "\n\n".join(parts)

    return f"""\
Analyze these {len(letters)} cover letters written by the same author. \
Extract a voice/style profile that can guide an agent to generate new \
cover letters and CVs that sound authentically like him.

Rules:
- Be specific and actionable - a prompt engineer must be able to reproduce \
this voice from these fields alone.
- Quote real phrases from the letters where possible.
- His English is B2 level - language_specific_traits should reflect \
technical competence without pretending native fluency.
- Never invent traits not evidenced by the letters.
- Output ONLY a single JSON object matching the exact shape below. No \
markdown fences, no prose before or after.

Shape: {{"opening_style": str, "closing_style": str, "sentence_rhythm": str, "recurring_phrases": [str], "avoided_patterns": str, "language_specific_traits": str, "tone_summary": [str]}}

Cover letters:
{text}
"""
