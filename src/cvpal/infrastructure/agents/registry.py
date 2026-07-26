"""Maps an agent name to a factory that builds its TextCompletionPort.

Adding a new CLI-driven provider (Codex, Gemini CLI, ...) means writing a
CliAgentSpec in infrastructure/agents/cli/ and adding one line to _SPECS
below - no changes anywhere else in the codebase.
"""

from __future__ import annotations

from cvpal.domain.ports.text_completion import TextCompletionPort
from cvpal.infrastructure.agents.cli.claude_code import CLAUDE_CODE
from cvpal.infrastructure.agents.cli.opencode import OPENCODE
from cvpal.infrastructure.agents.cli_adapter import CliAgentAdapter
from cvpal.infrastructure.agents.spec import CliAgentSpec

_SPECS: dict[str, CliAgentSpec] = {
    "opencode": OPENCODE,
    "claude-code": CLAUDE_CODE,
}


def available_agents() -> list[str]:
    return sorted(_SPECS)


def spec_for(name: str) -> CliAgentSpec | None:
    """Used by `cvpal doctor` to check the configured agent's binary is on
    PATH without building a full adapter (no completion call needed)."""
    return _SPECS.get(name)


def build_agent(name: str) -> TextCompletionPort:
    try:
        spec = _SPECS[name]
    except KeyError:
        raise ValueError(
            f"Unknown agent '{name}'. Available: {', '.join(available_agents())}"
        ) from None
    return CliAgentAdapter(spec)
