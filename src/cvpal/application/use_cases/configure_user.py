"""Writes/updates ~/.config/cvpal/config.toml.

Shared by two entry points that both need to persist the same settings:
`cvpal init` (the terminal wizard) and the MCP `configure` tool (so a
connected host agent can walk a brand-new user through setup
conversationally - see interfaces/mcp/server.py - without a terminal in
the loop at all). Merges into whatever's already there rather than
overwriting, since either caller may only be setting a subset of fields
(e.g. the MCP flow typically sets raw_dir + default_language first, name/
slug/contact details later or not at all).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

_USER_FIELDS = ("name", "slug", "default_language")
_PREFERRED_VALUE_FIELDS = ("phone", "linkedin", "github")


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _load_existing(config_file: Path) -> dict:
    if not config_file.exists():
        return {}
    with config_file.open("rb") as handle:
        return tomllib.load(handle)


def _render_toml(config: dict) -> str:
    lines: list[str] = []
    user = config.get("user", {})
    if user:
        lines.append("[user]")
        for key in _USER_FIELDS:
            if key in user:
                lines.append(f'{key} = "{_escape(user[key])}"')
        preferred = user.get("preferred_values", {})
        if preferred:
            lines.append("")
            lines.append("[user.preferred_values]")
            for key in _PREFERRED_VALUE_FIELDS:
                if key in preferred:
                    lines.append(f'{key} = "{_escape(preferred[key])}"')

    paths = config.get("paths", {})
    if paths:
        lines.append("")
        lines.append("[paths]")
        for key, value in paths.items():
            lines.append(f'{key} = "{_escape(value)}"')

    agent = config.get("agent", {})
    if agent:
        lines.append("")
        lines.append("[agent]")
        for key, value in agent.items():
            lines.append(f'{key} = "{_escape(value)}"')

    return "\n".join(lines) + "\n"


def write_user_config(
    config_file: Path,
    *,
    name: str | None = None,
    slug: str | None = None,
    default_language: str | None = None,
    phone: str | None = None,
    linkedin: str | None = None,
    github: str | None = None,
    raw_dir: str | None = None,
    provider: str | None = None,
) -> dict:
    """Merges any given (non-None) fields into config_file's existing
    content and writes the result back. Returns the resulting config as a
    plain dict, for the caller to confirm back to the user/host agent.
    """
    config = _load_existing(config_file)
    user = dict(config.get("user", {}))
    preferred = dict(user.get("preferred_values", {}))

    if name is not None:
        user["name"] = name
    if slug is not None:
        user["slug"] = slug
    if default_language is not None:
        user["default_language"] = default_language
    if phone is not None:
        preferred["phone"] = phone
    if linkedin is not None:
        preferred["linkedin"] = linkedin
    if github is not None:
        preferred["github"] = github
    if preferred:
        user["preferred_values"] = preferred
    config["user"] = user

    paths = dict(config.get("paths", {}))
    if raw_dir is not None:
        paths["raw_dir"] = raw_dir
    if paths:
        config["paths"] = paths

    agent = dict(config.get("agent", {}))
    if provider is not None:
        agent["provider"] = provider
    if agent:
        config["agent"] = agent

    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(_render_toml(config))
    return config
