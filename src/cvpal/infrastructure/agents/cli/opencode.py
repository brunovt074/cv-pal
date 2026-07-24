"""opencode CLI spec.

cv-pal shells out to the already locally-authenticated `opencode` CLI
instead of reading its credential store directly - it reuses the session
that's already logged in. See AGENTS.md Decision Log.

Note: opencode is a full agentic harness with file/bash/MCP/webfetch
tools. In non-interactive `run` mode those tool-call permissions are
auto-*denied* (no one is there to approve them), which silently produces
an empty response instead of an error - we forbid tool use in every
prompt and keep responses small (callers should split large structuring
jobs into per-section calls) rather than fight this. `opencode run --auto`
auto-approves permissions and may lift this restriction later; not
exercised yet.
"""

from __future__ import annotations

import json

from cvpal.domain.capabilities import Capability
from cvpal.domain.ports.text_completion import CompletionRequest
from cvpal.infrastructure.agents.spec import CliAgentSpec

_NO_TOOLS_INSTRUCTION = (
    "\n\nIMPORTANT: Do not use any tools (no file writes, no bash, no search). "
    "Reply directly in the chat with the requested content as plain text, "
    "however long it is."
)


def _build_argv(request: CompletionRequest, model: str) -> list[str]:
    return ["run", "-m", model, "--format", "json", request.prompt + _NO_TOOLS_INSTRUCTION]


def _parse_stdout(stdout: str) -> str:
    """Concatenate assistant text events, deduped by part id (opencode's
    JSON event stream can repeat a part while it's still streaming).
    """
    seen_part_ids: set[str] = set()
    text_parts: list[str] = []
    for line in stdout.splitlines():
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
    return "".join(text_parts)


OPENCODE = CliAgentSpec(
    name="opencode",
    default_binary="opencode",
    binary_env_var="OPENCODE_BIN",
    default_model="opencode-go/deepseek-v4-pro",
    model_env_var="OPENCODE_MODEL",
    build_argv=_build_argv,
    parse_stdout=_parse_stdout,
    capabilities=frozenset({Capability.TEXT_COMPLETION, Capability.JSON_COMPLETION}),
)
