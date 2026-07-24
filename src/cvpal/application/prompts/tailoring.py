"""Prompt for CV tailoring - see skills/cv-generation/SKILL.md.

The knowledge base is passed in as its rendered markdown (the same file a
human edits), not the typed domain model - this is deliberately the exact
artifact any agent (opencode today, anything else tomorrow) reads.
"""

from __future__ import annotations


def tailor_cv_prompt(knowledge_base_markdown: str, job_posting_text: str, language: str) -> str:
    return f"""\
You are drafting a CV tailored to one specific job posting, using ONLY the \
material in the knowledge base below - the single source of truth for the \
author's real experience, skills, and voice.

Rules:
- NEVER invent experience, skills, certifications, or projects absent from \
the knowledge base. If the posting calls for something not present, \
honestly omit it or frame the closest real, adjacent experience - never \
fabricate.
- Select only the subset of experience bullets, skills, and projects that \
are actually relevant to this posting - a tailored CV is not the entire \
history dumped verbatim.
- Write the CV in {language}.
- Match the tone described in the Voice Profile section of the knowledge \
base.
- Output a complete CV in markdown: header/contact info, a 2-3 sentence \
summary tailored to the role, relevant experience (grouped by \
company/role, most relevant first), relevant skills, relevant \
education/certifications.
- Output ONLY the CV markdown - no explanation, no preamble, no markdown \
fences.

Knowledge base:
{knowledge_base_markdown}

Job posting:
{job_posting_text}
"""
