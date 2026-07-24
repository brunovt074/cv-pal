"""Claude Code CLI spec — second adapter, exists to prove the CliAgentSpec
abstraction actually holds and isn't shaped around opencode alone.

`claude -p --output-format json <prompt>` returns a single JSON object
(`{"type": "result", "subtype": "success", "is_error": bool, "result": str,
...}`). Like opencode, non-interactive mode should not be granted tool
access for a pure text-completion call - the prompt explicitly forbids it
rather than passing --allowedTools.
"""

from __future__ import annotations

import json

from cvpal.domain.capabilities import Capability
from cvpal.domain.ports.text_completion import CompletionRequest
from cvpal.infrastructure.agents.spec import CliAgentSpec

_NO_TOOLS_INSTRUCTION = (
    "\n\nIMPORTANT: Do not use any tools (no file writes, no bash, no search). "
    "Reply directly with the requested content as plain text, however long it is."
)


def _build_argv(request: CompletionRequest, model: str) -> list[str]:
    return [
        "-p",
        "--output-format",
        "json",
        "--model",
        model,
        request.prompt + _NO_TOOLS_INSTRUCTION,
    ]


def _parse_stdout(stdout: str) -> str:
    stripped = stdout.strip()
    if not stripped:
        return ""
    try:
        event = json.loads(stripped)
    except json.JSONDecodeError:
        return ""
    if event.get("is_error"):
        return ""
    return event.get("result", "") or ""


CLAUDE_CODE = CliAgentSpec(
    name="claude-code",
    default_binary="claude",
    binary_env_var="CLAUDE_CODE_BIN",
    default_model="sonnet",
    model_env_var="CLAUDE_CODE_MODEL",
    build_argv=_build_argv,
    parse_stdout=_parse_stdout,
    capabilities=frozenset({Capability.TEXT_COMPLETION, Capability.JSON_COMPLETION}),
)
