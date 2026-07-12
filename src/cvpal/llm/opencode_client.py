"""Thin wrapper around the `opencode` CLI, used as this project's LLM backend.

Decision (see AGENTS.md Decision Log): cv-pal shells out to the already
locally-authenticated `opencode` CLI with model `opencode-go/deepseek-v4-pro`
for text-in/text-out tasks (translation, dedupe/structuring, voice profile
extraction) instead of calling a provider SDK directly. This avoids reading
opencode's own credential store - it reuses the session that's already
logged in.

Document generation (Agent Skills for .docx/.pdf) and job-posting fetch
(server-side web_fetch) in Fase 4 are Anthropic-specific capabilities with no
equivalent here and still go through the Anthropic SDK directly - see
skills/cv-generation/SKILL.md.

Note: opencode is a full agentic harness with file/bash tools. For large
outputs it may spontaneously try to write a scratch file instead of
replying with chat text - but tool-call permissions are auto-*denied* in
this non-interactive `run` mode (no one is there to approve them), which
silently produces an empty response instead of an error. We explicitly
forbid tool use in every prompt and keep individual calls small (callers
should split large structuring jobs into per-section calls) rather than
fight this - see analytics/structure.py for the per-section splitting.
"""

from __future__ import annotations

import json
import os
import subprocess

DEFAULT_MODEL = "opencode-go/deepseek-v4-pro"
DEFAULT_TIMEOUT_SECONDS = 600

_NO_TOOLS_INSTRUCTION = (
    "\n\nIMPORTANT: Do not use any tools (no file writes, no bash, no search). "
    "Reply directly in the chat with the requested content as plain text, "
    "however long it is."
)


class OpenCodeCallError(RuntimeError):
    pass


def call_opencode(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    """Run a single non-interactive `opencode run` invocation and return the
    concatenated assistant text response.

    Each invocation pays a large fixed context overhead (the CLI injects its
    own agent/project context) - batch work into as few calls as possible
    rather than looping per-record, but keep each call's *output* small (see
    module docstring on tool-call permission denial for large outputs).
    """
    binary = os.environ.get("OPENCODE_BIN", "opencode")
    result = subprocess.run(
        [binary, "run", "-m", model, "--format", "json", prompt + _NO_TOOLS_INSTRUCTION],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise OpenCodeCallError(
            f"opencode run failed (exit {result.returncode}): {result.stderr[:2000]}"
        )

    seen_part_ids: set[str] = set()
    text_parts: list[str] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "text":
            continue
        part = event.get("part", {})
        part_id = part.get("id")
        part_text = part.get("text")
        if not part_text or part_id in seen_part_ids:
            continue
        seen_part_ids.add(part_id)
        text_parts.append(part_text)

    if not text_parts:
        raise OpenCodeCallError(
            "opencode run produced no text output (it may have attempted a tool "
            f"call that was denied). stdout tail: {result.stdout[-2000:]}"
        )
    return "".join(text_parts)


def _strip_markdown_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines)


def call_opencode_json(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict | list:
    """Call opencode with a prompt that must return JSON, and parse it.

    Tolerates a response wrapped in a markdown code fence, which models
    sometimes add even when explicitly told not to. Keep prompts scoped so
    the expected output is small - see module docstring.
    """
    text = call_opencode(prompt, model=model, timeout=timeout)
    stripped = _strip_markdown_fence(text)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise OpenCodeCallError(
            f"opencode response was not valid JSON: {exc}. Response head: {stripped[:500]}"
        ) from exc
