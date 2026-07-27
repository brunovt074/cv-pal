"""Turns a TextCompletionPort's raw text response into typed data.

Every agent occasionally wraps JSON in a markdown fence even when told not
to - tolerate it here once, instead of in every use case.
"""

from __future__ import annotations

import json

from pydantic import TypeAdapter

from cvpal.domain.errors import InvalidAgentResponseError
from cvpal.domain.ports.text_completion import TextCompletionPort


def strip_markdown_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines)


def parse_json_response(agent_name: str, text: str) -> dict | list:
    """Parse the first complete JSON value in the response.

    Uses `raw_decode` rather than `json.loads` because agents occasionally
    append trailing prose/commentary after a valid JSON value - a strict
    `json.loads` rejects the whole response as "Extra data" even though the
    JSON itself is fine. `raw_decode` stops at the end of the first value
    and ignores whatever comes after.
    """
    stripped = strip_markdown_fence(text)
    try:
        value, _end = json.JSONDecoder().raw_decode(stripped)
        return value
    except json.JSONDecodeError as exc:
        raise InvalidAgentResponseError(
            agent_name, f"response was not valid JSON: {exc}", raw_response=stripped[:2000]
        ) from exc


def complete_as(agent: TextCompletionPort, agent_name: str, prompt: str, model_type: type):
    """Call the agent expecting JSON, parse it, and validate it against a
    pydantic model or a `list[Model]` / `dict` type via TypeAdapter.
    """
    from cvpal.domain.ports.text_completion import CompletionRequest

    result = agent.complete(CompletionRequest(prompt=prompt, expects_json=True))
    raw = parse_json_response(agent_name, result.text)
    return TypeAdapter(model_type).validate_python(raw)
