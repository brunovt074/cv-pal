"""Prompt templates for the structuring pass - one agent call per canonical
CV section, kept small and independently checkpointed (see
application/use_cases/build_knowledge_base.py and
skills/data-analytics/SKILL.md for the rationale).

Each prompt asks for JSON matching a domain model's shape, validated via
application/services/response_parsing.complete_as against the pydantic
models in domain/knowledge/models.py.
"""

from __future__ import annotations

from cvpal.application.services.dedupe import DedupedBlock

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


def personal_data_prompt(blocks: list[DedupedBlock]) -> str:
    return f"""\
Extract personal contact/profile data (name, phone, email, location, \
job-title headline, and full URLs for linkedin/github/portfolio/project \
links) from these CV header and links blocks. One record per distinct \
field/value pair - if the SAME field (e.g. "phone") has multiple distinct \
values across CV variants, output one record per distinct value, do not \
silently pick one or merge them; a later deterministic pass resolves which \
one is current. Use the actual URL as the value for linkedin/github/project \
link fields, not the anchor text.

{_COMMON_RULES}
Shape: [{{"field": str, "value": str, "source_files": [str]}}]

Input:
{_format_blocks(blocks)}
"""


def summary_prompt(blocks: list[DedupedBlock]) -> str:
    return f"""\
Consolidate these professional-summary paragraphs into distinct variants \
(e.g. a Java/backend-focused variant, a PHP-focused variant, a full-stack \
variant) - merge near-duplicate phrasing into one variant per distinct \
angle, don't create a variant per source file.

{_COMMON_RULES}
Shape: [{{"variant_label": str, "text": str, "source_files": [str]}}]

Input:
{_format_blocks(blocks)}
"""


def experience_prompt(blocks: list[DedupedBlock]) -> str:
    return f"""\
Structure these work-experience lines into individual bullets grouped by \
role. Lines about the same company/role/period share one company, role, \
start_date, end_date, modality, location - but each distinct \
accomplishment/task is its OWN entry (its own "bullet" text) in the output \
list, repeating the shared company/role/dates fields. Include modality \
(Remote, On-site, Hybrid) and location when available. Also include \
non-employment sections like "Work Simulations" and freelance/self-employed \
work as their own entries. Commercial/customer-service roles are relevant \
context, include them. Dates in MM/YYYY format where possible.

{_COMMON_RULES}
Shape: [{{"company": str, "role": str, "start_date": str, "end_date": str, "modality": str, "location": str, "bullet": str, "tech_tags": [str], "source_files": [str]}}]

Input:
{_format_blocks(blocks)}
"""


def education_and_certifications_prompt(blocks: list[DedupedBlock]) -> str:
    return f"""\
Split these lines into formal education entries (degrees, technical \
programs) versus standalone certifications (short courses, online \
certificates, e.g. "Google/Coursera Data Analytics Certification").

{_COMMON_RULES}
Shape: {{"education": [{{"institution": str, "program": str, "program_type": str, "date": str, "status": str, "source_files": [str]}}], "certifications": [{{"name": str, "issuer": str, "date": str, "source_files": [str]}}]}}

Input:
{_format_blocks(blocks)}
"""


def skills_prompt(blocks: list[DedupedBlock]) -> str:
    return f"""\
Extract individual skills (languages, frameworks, databases, tools) from \
these skills-section lines. One record per distinct skill, not per line - \
a single line often lists many skills.

{_COMMON_RULES}
Shape: [{{"skill": str, "category": str, "seniority": str, "years": str, "evidence": str, "source_files": [str]}}]

Categories to use: language, framework, database, tool, practice, ai, os, cloud, other.
Seniority is a best-guess placeholder (Jr, Ssr, Sr) - to be adjusted manually later.
Years: a best-guess estimate from CV context, "" if there's no evidence.
Evidence: one short phrase from the CV that supports this skill.

Input:
{_format_blocks(blocks)}
"""


def projects_prompt(blocks: list[DedupedBlock]) -> str:
    return f"""\
Consolidate these personal-project lines into distinct projects (merge \
lines describing the same project into one entry with a combined \
description).

{_COMMON_RULES}
Shape: [{{"name": str, "description": str, "tech": [str], "role": str, "source_files": [str]}}]

Input:
{_format_blocks(blocks)}
"""


def languages_prompt(blocks: list[DedupedBlock]) -> str:
    return f"""\
Extract one record per distinct human language spoken, with proficiency \
level, from these lines.

{_COMMON_RULES}
Shape: [{{"language": str, "level": str, "source_files": [str]}}]

Input:
{_format_blocks(blocks)}
"""
