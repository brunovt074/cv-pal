"""LLM-backed structuring: turn mechanically-deduped raw CV text into the
final English-language, structured knowledge base records.

Why an LLM here and not more regex: company/role/date extraction and
semantic deduplication (the same bullet reworded across CV variants) is
exactly the kind of free-text interpretation that's fragile to hand-roll
across ~38 differently-formatted source documents. See
skills/data-analytics/SKILL.md.

Split into one small call per canonical section (rather than one giant
call) - see llm/opencode_client.py docstring on why large outputs are
unreliable in this harness, and it keeps each call independently debuggable.
"""

from __future__ import annotations

from pathlib import Path

from cvpal.analytics.checkpoint import with_checkpoint_list, with_checkpoint_raw
from cvpal.analytics.dedupe import DedupedBlock, dedupe_section_lines
from cvpal.analytics.models import (
    CertificationEntry,
    EducationEntry,
    ExperienceBullet,
    LanguageEntry,
    PersonalDataField,
    ProjectEntry,
    SkillEntry,
    StructuredKnowledgeBase,
    SummaryEntry,
)
from cvpal.ingest.models import RawDocument
from cvpal.llm.opencode_client import call_opencode_json

_COMMON_RULES = """\
Rules:
- ALL output text MUST be in English, regardless of source language. \
Translate faithfully - do not embellish, do not invent claims not present \
in the source.
- Merge lines describing the same underlying fact into ONE record.
- Never invent a fact (company, role, date, skill) absent from the input.
- Preserve source_files: copy file names from the "[...]" tag(s) at the \
start of each input line into that record's source_files list. Cap this at \
AT MOST 3 representative file names per record, even if the fact appears in \
many more files - do not list every duplicate, this is just traceability, \
not a complete audit trail.
- Output ONLY a single JSON value matching the exact shape below. No \
markdown fences, no prose before or after.
"""


def _format_blocks(blocks: list[DedupedBlock]) -> str:
    return "\n".join(f"- [{', '.join(b.source_files)}] {b.text}" for b in blocks)


def structure_personal_data(documents: list[RawDocument]) -> list[PersonalDataField]:
    blocks = dedupe_section_lines(documents, "header") + dedupe_section_lines(documents, "links")
    if not blocks:
        return []
    prompt = f"""\
Extract personal contact/profile data (name, phone, email, location, \
job-title headline, and full URLs for linkedin/github/portfolio/project \
links) from these CV header and links blocks. One record per distinct \
field - use the actual URL as the value for linkedin/github/project link \
fields, not the anchor text (e.g. field "linkedin", value the full \
https://linkedin.com/... URL).

{_COMMON_RULES}
Shape: [{{"field": str, "value": str, "source_files": [str]}}]

Input:
{_format_blocks(blocks)}
"""
    raw = call_opencode_json(prompt)
    return [PersonalDataField.model_validate(r) for r in raw]


def structure_summaries(documents: list[RawDocument]) -> list[SummaryEntry]:
    blocks = dedupe_section_lines(documents, "summary")
    if not blocks:
        return []
    prompt = f"""\
Consolidate these professional-summary paragraphs into distinct variants \
(e.g. a Java/backend-focused variant, a PHP-focused variant, a full-stack \
variant) - merge near-duplicate phrasing into one variant per distinct \
angle, don't create a variant per source file.

{_COMMON_RULES}
Shape: [{{"variant_label": str, "text": str, "source_files": [str]}}]

Input:
{_format_blocks(blocks)}
"""
    raw = call_opencode_json(prompt)
    return [SummaryEntry.model_validate(r) for r in raw]


def structure_experience(documents: list[RawDocument]) -> list[ExperienceBullet]:
    blocks = dedupe_section_lines(documents, "experience")
    prompt = f"""\
Structure these work-experience lines into individual bullets grouped by \
role. Lines about the same company/role/period share one company, role, \
start_date, end_date, modality, location - but each distinct \
accomplishment/task is its OWN entry (its own "bullet" text) in the output \
list, repeating the shared company/role/dates fields.

{_COMMON_RULES}
Shape: [{{"company": str, "role": str, "start_date": str, "end_date": str, "modality": str, "location": str, "bullet": str, "tech_tags": [str], "source_files": [str]}}]

Input:
{_format_blocks(blocks)}
"""
    raw = call_opencode_json(prompt)
    return [ExperienceBullet.model_validate(r) for r in raw]


def structure_education_and_certifications(
    documents: list[RawDocument],
) -> tuple[list[EducationEntry], list[CertificationEntry]]:
    blocks = dedupe_section_lines(documents, "education")
    if not blocks:
        return [], []
    prompt = f"""\
Split these lines into formal education entries (degrees, technical \
programs) versus standalone certifications (short courses, online \
certificates, e.g. "Google/Coursera Data Analytics Certification").

{_COMMON_RULES}
Shape: {{"education": [{{"institution": str, "program": str, "program_type": str, "date": str, "status": str, "source_files": [str]}}], "certifications": [{{"name": str, "issuer": str, "date": str, "source_files": [str]}}]}}

Input:
{_format_blocks(blocks)}
"""
    raw = call_opencode_json(prompt)
    education = [EducationEntry.model_validate(r) for r in raw.get("education", [])]
    certifications = [CertificationEntry.model_validate(r) for r in raw.get("certifications", [])]
    return education, certifications


def structure_skills(documents: list[RawDocument]) -> list[SkillEntry]:
    blocks = dedupe_section_lines(documents, "skills")
    prompt = f"""\
Extract individual skills (languages, frameworks, databases, tools) from \
these skills-section lines. One record per distinct skill, not per line - \
a single line often lists many skills.

{_COMMON_RULES}
Shape: [{{"skill": str, "category": str, "evidence": str, "source_files": [str]}}]

Categories to use: "language", "framework", "database", "tool", "practice".

Input:
{_format_blocks(blocks)}
"""
    raw = call_opencode_json(prompt)
    return [SkillEntry.model_validate(r) for r in raw]


def structure_projects(documents: list[RawDocument]) -> list[ProjectEntry]:
    blocks = dedupe_section_lines(documents, "projects")
    if not blocks:
        return []
    prompt = f"""\
Consolidate these personal-project lines into distinct projects (merge \
lines describing the same project into one entry with a combined \
description).

{_COMMON_RULES}
Shape: [{{"name": str, "description": str, "tech": [str], "role": str, "source_files": [str]}}]

Input:
{_format_blocks(blocks)}
"""
    raw = call_opencode_json(prompt)
    return [ProjectEntry.model_validate(r) for r in raw]


def structure_languages(documents: list[RawDocument]) -> list[LanguageEntry]:
    blocks = dedupe_section_lines(documents, "languages")
    if not blocks:
        return []
    prompt = f"""\
Extract one record per distinct human language spoken, with proficiency \
level, from these lines.

{_COMMON_RULES}
Shape: [{{"language": str, "level": str, "source_files": [str]}}]

Input:
{_format_blocks(blocks)}
"""
    raw = call_opencode_json(prompt)
    return [LanguageEntry.model_validate(r) for r in raw]


def structure_knowledge_base(
    documents: list[RawDocument], checkpoint_dir: Path | None = None
) -> StructuredKnowledgeBase:
    """Run all structuring calls, checkpointing each to `checkpoint_dir` if
    given so a killed/interrupted run can resume from where it left off
    instead of re-paying every LLM call.
    """
    cvs = [d for d in documents if d.doc_kind == "cv"]

    if checkpoint_dir is None:
        education, certifications = structure_education_and_certifications(cvs)
        return StructuredKnowledgeBase(
            personal_data=structure_personal_data(cvs),
            summaries=structure_summaries(cvs),
            experience=structure_experience(cvs),
            education=education,
            certifications=certifications,
            skills=structure_skills(cvs),
            projects=structure_projects(cvs),
            languages=structure_languages(cvs),
        )

    personal_data = with_checkpoint_list(
        checkpoint_dir / "personal_data.json", PersonalDataField, lambda: structure_personal_data(cvs)
    )
    summaries = with_checkpoint_list(
        checkpoint_dir / "summaries.json", SummaryEntry, lambda: structure_summaries(cvs)
    )
    experience = with_checkpoint_list(
        checkpoint_dir / "experience.json", ExperienceBullet, lambda: structure_experience(cvs)
    )

    def _edu_certs_as_dict() -> dict:
        education, certifications = structure_education_and_certifications(cvs)
        return {
            "education": [e.model_dump() for e in education],
            "certifications": [c.model_dump() for c in certifications],
        }

    edu_certs_raw = with_checkpoint_raw(checkpoint_dir / "education_certifications.json", _edu_certs_as_dict)
    education = [EducationEntry.model_validate(e) for e in edu_certs_raw["education"]]
    certifications = [CertificationEntry.model_validate(c) for c in edu_certs_raw["certifications"]]

    skills = with_checkpoint_list(
        checkpoint_dir / "skills.json", SkillEntry, lambda: structure_skills(cvs)
    )
    projects = with_checkpoint_list(
        checkpoint_dir / "projects.json", ProjectEntry, lambda: structure_projects(cvs)
    )
    languages = with_checkpoint_list(
        checkpoint_dir / "languages.json", LanguageEntry, lambda: structure_languages(cvs)
    )

    return StructuredKnowledgeBase(
        personal_data=personal_data,
        summaries=summaries,
        experience=experience,
        education=education,
        certifications=certifications,
        skills=skills,
        projects=projects,
        languages=languages,
    )
