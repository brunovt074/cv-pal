"""Deterministic corrections to agent-extracted personal data.

Which phone number / LinkedIn URL / GitHub username is *current* across
~50 CV variants spanning years is a fact only the author can supply - an
agent must never guess it. This applies the known-authoritative values as
a post-processing pass, tagging every extracted value as current or
previous rather than silently dropping the others (traceability).
"""

from __future__ import annotations

import re

from cvpal.domain.knowledge.models import PersonalDataField

PREFERRED_VALUES: dict[str, str] = {
    "phone": "+5493772566242",
    "linkedin": "https://www.linkedin.com/in/bruno-vargas-tettamanti-dev/",
    "github": "brunovt074",
}

_URL_PREFIX = re.compile(r"^https?://(www\.)?(linkedin\.com/in/|github\.com/)?")


def _digits_only(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def _normalize_identifier(value: str) -> str:
    """Strip protocol/domain so 'brunovt074' and
    'https://github.com/brunovt074' compare equal - and, critically,
    compares the full slug rather than a substring, so
    'bruno-vargas-tettamanti-dev' never accidentally matches
    'bruno-vargas-tettamanti-developer'.
    """
    return _URL_PREFIX.sub("", value.strip().lower()).rstrip("/")


def _matches_preferred(field: str, value: str, preferred: str) -> bool:
    if field == "phone":
        digits = _digits_only(value)
        return bool(digits) and digits.endswith(_digits_only(preferred))
    return _normalize_identifier(value) == _normalize_identifier(preferred)


def apply_known_corrections(fields: list[PersonalDataField]) -> list[PersonalDataField]:
    resolved: list[PersonalDataField] = []
    for entry in fields:
        field_key = entry.field.strip().lower()
        preferred = PREFERRED_VALUES.get(field_key)
        if preferred is None:
            resolved.append(entry)
            continue
        label = "(current)" if _matches_preferred(field_key, entry.value, preferred) else "(previous)"
        resolved.append(entry.model_copy(update={"value": f"{entry.value.strip()} {label}"}))
    return resolved
