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
history dumped verbatim. The exceptions: always include teaching, \
mentoring, or instructor roles if present in the knowledge base, even \
when the posting is purely technical - they broaden the skill set \
(frontend stacks, frameworks) and demonstrate knowledge transfer / \
communication skills that hiring managers consistently value.
- Order experience by relevance and current impact, not strictly by \
date: (1) current role first, (2) mentoring/teaching roles right after, \
(3) freelance and side projects, (4) work simulations and internships \
last as the least important. Follow the Professional Direction section \
in the knowledge base for this and other editorial guidelines.
- Write the CV in {language}.
- Match the tone described in the Voice Profile section of the knowledge \
base.
- Output a complete CV in markdown: header/contact info, a 2-3 sentence \
summary tailored to the role, relevant experience (grouped by \
company/role, most relevant first), relevant skills, relevant \
education/certifications.
- For emphasis, use **bold** with double asterisks (e.g. **Java**, \
**(04/2024 – Present)**), not single asterisks. Single-asterisk italic \
isn't supported by the renderer, so `*text*` will not appear bold in the \
final PDF/docx.
- For the Skills section, use one line per category, with **only the \
category label in bold** (followed by a colon), and the list of skills \
in plain text. Example: `**Frameworks:** Spring Boot, Spring Security, \
Hibernate, FastAPI, Laravel, React, Next.js` — NOT \
`**Frameworks: Spring Boot, Spring Security, ...**`. The whole-line \
format makes the values illegible in the final PDF.
- Output ONLY the CV markdown - no explanation, no preamble, no markdown \
fences.

Knowledge base:
{knowledge_base_markdown}

Job posting:
{job_posting_text}
"""
