"""Compact markdown projection of the knowledge base for agent consumption.

`data/knowledge-base.md` (via MarkdownKnowledgeRepository) is the full
source of truth, provenance included - useful for a human auditing where a
fact came from. An agent drafting a CV never needs that: `source_files` is
pure overhead, and a personal-data value tagged `(previous)` by
application/services/personal_data_resolution.py is a superseded fact, not
a choice to offer. Stripping both is most of the token savings; everything
an agent could plausibly want to select from (summary variants, every
experience bullet, every skill, every distinct headline phrasing, ...)
stays untouched.
"""

from __future__ import annotations

from cvpal.domain.knowledge.models import KnowledgeBase


def _is_previous_variant(value: str) -> bool:
    return value.strip().endswith("(previous)")


def _clean_current_marker(value: str) -> str:
    return value.replace(" (current)", "").strip()


def _render_personal_data(kb: KnowledgeBase) -> str:
    lines = ["## Personal Data"]
    for entry in kb.personal_data:
        if _is_previous_variant(entry.value):
            continue
        lines.append(f"- **{entry.field}**: {_clean_current_marker(entry.value)}")
    return "\n".join(lines)


def _render_summaries(kb: KnowledgeBase) -> str:
    lines = ["## Summary"]
    for entry in kb.summaries:
        lines.append(f"**{entry.variant_label}**: {entry.text}")
    return "\n".join(lines)


def _render_experience(kb: KnowledgeBase) -> str:
    lines = ["## Experience"]
    for e in kb.experience:
        meta = " | ".join(part for part in (e.modality, e.location) if part)
        header = f"### {e.company} — {e.role} ({e.start_date} – {e.end_date})"
        if meta:
            header += f" [{meta}]"
        lines.append(header)
        tags = f" `{'` `'.join(e.tech_tags)}`" if e.tech_tags else ""
        lines.append(f"- {e.bullet}{tags}")
    return "\n".join(lines)


def _render_education(kb: KnowledgeBase) -> str:
    lines = ["## Education"]
    for e in kb.education:
        lines.append(f"- {e.institution} — {e.program} ({e.date}) {e.status}".strip())
    return "\n".join(lines)


def _render_certifications(kb: KnowledgeBase) -> str:
    lines = ["## Certifications"]
    for c in kb.certifications:
        lines.append(f"- {c.name} — {c.issuer} ({c.date})".strip())
    return "\n".join(lines)


def _render_skills(kb: KnowledgeBase) -> str:
    lines = ["## Skills"]
    by_category: dict[str, list[str]] = {}
    for s in kb.skills:
        label = f"{s.skill} ({s.seniority})" if s.seniority else s.skill
        by_category.setdefault(s.category or "other", []).append(label)
    for category in sorted(by_category):
        lines.append(f"- **{category}**: {', '.join(by_category[category])}")
    return "\n".join(lines)


def _render_projects(kb: KnowledgeBase) -> str:
    lines = ["## Projects"]
    for p in kb.projects:
        tech = f" [{', '.join(p.tech)}]" if p.tech else ""
        lines.append(f"### {p.name}{tech}")
        lines.append(f"- {p.description}")
        if p.role:
            lines.append(f"- Role: {p.role}")
    return "\n".join(lines)


def _render_languages(kb: KnowledgeBase) -> str:
    lines = ["## Languages"]
    for entry in kb.languages:
        lines.append(f"- {entry.language}: {entry.level}")
    return "\n".join(lines)


def _render_voice_profile(kb: KnowledgeBase) -> str:
    if kb.voice_profile is None:
        return "## Voice Profile\n_(not yet extracted)_"
    voice = kb.voice_profile
    lines = ["## Voice Profile"]
    if voice.opening_style:
        lines.append(f"- Opening style: {voice.opening_style}")
    if voice.closing_style:
        lines.append(f"- Closing style: {voice.closing_style}")
    if voice.sentence_rhythm:
        lines.append(f"- Sentence rhythm: {voice.sentence_rhythm}")
    if voice.recurring_phrases:
        lines.append(f"- Recurring phrases: {'; '.join(voice.recurring_phrases)}")
    if voice.avoided_patterns:
        lines.append(f"- Avoids: {voice.avoided_patterns}")
    if voice.language_specific_traits:
        lines.append(f"- Language-specific traits: {voice.language_specific_traits}")
    if voice.tone_summary:
        lines.append(f"- Tone: {', '.join(voice.tone_summary)}")
    return "\n".join(lines)


_SECTION_RENDERERS = (
    _render_personal_data,
    _render_summaries,
    _render_experience,
    _render_education,
    _render_certifications,
    _render_skills,
    _render_projects,
    _render_languages,
    _render_voice_profile,
)


def render_agent_view(kb: KnowledgeBase) -> str:
    return "\n\n".join(renderer(kb) for renderer in _SECTION_RENDERERS)
