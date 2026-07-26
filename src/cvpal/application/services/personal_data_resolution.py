"""Deterministic corrections to agent-extracted personal data.

Which phone number / LinkedIn URL / GitHub username is *current* across
many CV variants spanning years is a fact only the author can supply - an
agent must never guess it. This applies the known-authoritative values as
a post-processing pass, tagging every extracted value as current or
previous rather than silently dropping the others (traceability).

The preferred values are per-user and never hardcoded: they read from
CVPAL_PHONE / CVPAL_LINKEDIN / CVPAL_GITHUB at call time (not import
time - .env is loaded by the CLI entry point after this module is first
imported), falling back to a placeholder identity if unset.
"""

from __future__ import annotations

import os
import re

from cvpal.domain.knowledge.models import PersonalDataField

_DEFAULT_PREFERRED_VALUES: dict[str, str] = {
    "phone": "+1-555-0100",
    "linkedin": "https://www.linkedin.com/in/alex-doe-dev/",
    "github": "alexdoe",
}

_ENV_OVERRIDES: dict[str, str] = {
    "phone": "CVPAL_PHONE",
    "linkedin": "CVPAL_LINKEDIN",
    "github": "CVPAL_GITHUB",
}


def _preferred_values() -> dict[str, str]:
    return {
        field: os.environ.get(env_var, _DEFAULT_PREFERRED_VALUES[field])
        for field, env_var in _ENV_OVERRIDES.items()
    }


_URL_PREFIX = re.compile(r"^https?://(www\.)?(linkedin\.com/in/|github\.com/)?")


def _digits_only(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def _normalize_identifier(value: str) -> str:
    """Strip protocol/domain so 'alexdoe' and
    'https://github.com/alexdoe' compare equal - and, critically,
    compares the full slug rather than a substring, so
    'alex-doe-dev' never accidentally matches 'alex-doe-developer'.
    """
    return _URL_PREFIX.sub("", value.strip().lower()).rstrip("/")


def _matches_preferred(field: str, value: str, preferred: str) -> bool:
    if field == "phone":
        digits = _digits_only(value)
        return bool(digits) and digits.endswith(_digits_only(preferred))
    return _normalize_identifier(value) == _normalize_identifier(preferred)


def apply_known_corrections(fields: list[PersonalDataField]) -> list[PersonalDataField]:
    preferred_values = _preferred_values()
    resolved: list[PersonalDataField] = []
    for entry in fields:
        field_key = entry.field.strip().lower()
        preferred = preferred_values.get(field_key)
        if preferred is None:
            resolved.append(entry)
            continue
        label = "(current)" if _matches_preferred(field_key, entry.value, preferred) else "(previous)"
        resolved.append(entry.model_copy(update={"value": f"{entry.value.strip()} {label}"}))
    return resolved
