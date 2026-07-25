"""Prompt for the `/cv-pal` MCP entry point.

The one-shot conversational flow: the host agent reads this, writes and
PRINTS a tailored CV directly in its own conversation/terminal, then asks
about a cover letter - branching on whether a voice profile has already
been captured for this author. See skills/cv-generation/SKILL.md and
skills/mcp-server/SKILL.md for the surrounding contract.
"""

from __future__ import annotations

from cvpal.domain.knowledge.voice import VoiceProfile

_RULES = """\
Rules:
- Use ONLY material present in the knowledge base below. Never invent a \
skill, role, company, date, certification, or project absent from it. If \
the posting calls for something not present, honestly omit it or frame \
the closest real, adjacent experience - never fabricate.
- Select only the subset of experience bullets, skills, and projects that \
are actually relevant to this posting - do not dump the entire history.
- Write in {language}."""


def _voice_branch(voice_profile: VoiceProfile | None) -> str:
    if voice_profile is None:
        return """\
No voice profile has been captured for this author yet. Before drafting \
the cover letter, do ONE of the following:
- Ask what tone they want (e.g. direct and technical, warm and \
enthusiastic, formal), or
- Offer a short example opening line and ask if that captures how they'd \
naturally write, or
- Ask which 2-3 aspects of their background they most want the letter to \
highlight.
Use their answer to write the letter, keeping the same factual \
constraints as the CV (only material from the knowledge base, tied to the \
posting)."""

    tone_summary = ", ".join(voice_profile.tone_summary) or "not summarized"
    opening = voice_profile.opening_style or "not captured"
    return f"""\
A voice profile IS already captured for this author: tone reads as \
"{tone_summary}", typical opening style is "{opening}". Before drafting \
the cover letter, summarize this captured essence in one or two sentences \
and ask the user if it's accurate, or if they'd like to resurface \
different aspects of their background - without losing sight of the job \
posting. Use their answer (or the captured profile as-is if they confirm \
it) to write the letter."""


def cv_pal_prompt(
    agent_view_markdown: str,
    posting_text: str,
    language: str,
    voice_profile: VoiceProfile | None,
) -> str:
    return f"""\
You are helping tailor a CV - and, if wanted, a cover letter - to the job \
posting below, using ONLY the knowledge base material provided.

{_RULES.format(language=language)}

Protocol:
1. Write the tailored CV and PRINT THE FULL TEXT in this conversation \
(plain markdown, ready to read) - do not just describe it, show it.
2. After the CV, ask the user if they'd also like a cover letter.
3. If yes: {_voice_branch(voice_profile)}
   Then write and print the cover letter the same way as the CV.

Knowledge base:
{agent_view_markdown}

Job posting:
{posting_text}
"""
