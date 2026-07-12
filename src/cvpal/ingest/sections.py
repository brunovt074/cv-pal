"""Section-header detection for CV documents.

Cover letters are free-form prose with no reliable section headers — they are
never run through this detector. Only CV documents get split into sections;
see `doc_kind` in `RawDocument`.
"""

from __future__ import annotations

import re

# Canonical section name -> header keywords seen across the corpus (ES + EN).
# Order matters only for readability; matching is keyword-based, not positional.
SECTION_KEYWORDS: dict[str, list[str]] = {
    "summary": [
        "resumen profesional",
        "professional summary",
        "perfil profesional",
        "summary",
        "profile",
    ],
    "experience": [
        "experiencia profesional",
        "professional experience",
        "experiencia laboral",
        "work experience",
        "experience",
    ],
    "education": [
        "educación y certificaciones",
        "education and certifications",
        "educación",
        "education",
        "formación académica",
    ],
    "certifications": [
        "certificaciones",
        "certifications",
    ],
    "skills": [
        "habilidades técnicas",
        "technical skills",
        "habilidades",
        "skills",
        "competencias técnicas",
    ],
    "projects": [
        "proyectos",
        "projects",
        "proyecto personal",
        "personal project",
    ],
    "languages": [
        "idiomas",
        "languages",
    ],
    "contact": [
        "contacto",
        "contact",
    ],
}

_HEADER_LINE_MAX_LEN = 60


_ES_STOPWORDS = {
    "que", "de", "la", "el", "en", "y", "con", "para", "por", "un", "una",
    "mi", "me", "muy", "más", "también", "trabajo", "equipo", "años", "soy",
}
_EN_STOPWORDS = {
    "the", "of", "and", "with", "for", "to", "in", "on", "my", "very",
    "also", "work", "team", "years", "am", "i", "this",
}


def _stopword_language_guess(full_text: str) -> str:
    """Fallback for prose with no CV section headers (e.g. cover letters):
    ratio of ES vs EN stopword hits among the words actually present.
    """
    words = re.findall(r"[a-záéíóúñ]+", full_text.lower())
    if not words:
        return "unknown"
    word_set = set(words)
    es_hits = len(word_set & _ES_STOPWORDS)
    en_hits = len(word_set & _EN_STOPWORDS)
    if es_hits == 0 and en_hits == 0:
        return "unknown"
    return "es" if es_hits >= en_hits else "en"


def detect_language(full_text: str) -> str:
    """Best-effort ES/EN detection. No LLM call.

    Tries CV section-header keywords first (higher precision); falls back to
    a stopword ratio for free-form prose (cover letters) that has no headers.
    """
    lowered = full_text.lower()
    es_markers = [
        "resumen profesional",
        "experiencia profesional",
        "educación",
        "habilidades técnicas",
        "presente",
    ]
    en_markers = [
        "professional summary",
        "professional experience",
        "education",
        "technical skills",
        "present",
    ]
    es_hits = sum(1 for m in es_markers if m in lowered)
    en_hits = sum(1 for m in en_markers if m in lowered)
    if es_hits == 0 and en_hits == 0:
        return _stopword_language_guess(full_text)
    return "es" if es_hits >= en_hits else "en"


def split_into_sections(full_text: str) -> dict[str, str]:
    """Split raw CV text into canonical sections by scanning for header lines.

    A line is a candidate header if it's short, and its normalized text
    matches (via substring) one of the keywords in SECTION_KEYWORDS. Content
    before the first detected header is bucketed as "header" (name/contact
    block at the top of the CV).
    """
    lines = full_text.splitlines()
    keyword_to_section = {
        kw: name for name, kws in SECTION_KEYWORDS.items() for kw in kws
    }

    boundaries: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) > _HEADER_LINE_MAX_LEN:
            continue
        normalized = re.sub(r"[^a-záéíóúñ ]", "", stripped.lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        for kw, section_name in keyword_to_section.items():
            if kw in normalized:
                boundaries.append((idx, section_name))
                break

    if not boundaries:
        return {"unstructured": full_text}

    sections: dict[str, str] = {}
    first_start = boundaries[0][0]
    if first_start > 0:
        sections["header"] = "\n".join(lines[:first_start]).strip()

    for i, (start, name) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(lines)
        body = "\n".join(lines[start + 1 : end]).strip()
        if name in sections:
            sections[name] = f"{sections[name]}\n\n{body}"
        else:
            sections[name] = body

    return sections
