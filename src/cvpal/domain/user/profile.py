"""The author's identity, as data - never hardcoded in application code.

Every piece that used to hardcode a name/slug/contact detail
(`personal_data_resolution.py`, `output_naming.py`,
`markdown_knowledge_repository.py`) now takes a `UserProfile` instead,
built once by `config.Settings` from `~/.config/cvpal/config.toml` (see
PROJECT_STATUS.md) and threaded through `Container`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

DEFAULT_NAME = "Alex Doe"
DEFAULT_SLUG = "alex-doe"
DEFAULT_LANGUAGE = "en"
DEFAULT_PREFERRED_VALUES: dict[str, str] = {
    "phone": "+1-555-0100",
    "linkedin": "https://www.linkedin.com/in/alex-doe-dev/",
    "github": "alexdoe",
}


class UserProfile(BaseModel):
    name: str = DEFAULT_NAME
    slug: str = DEFAULT_SLUG
    default_language: str = DEFAULT_LANGUAGE
    preferred_values: dict[str, str] = Field(default_factory=lambda: dict(DEFAULT_PREFERRED_VALUES))
