"""Maps an agent name to a factory that builds its TextCompletionPort.

Adding a new CLI-driven provider (Codex, Gemini CLI, ...) means writing a
CliAgentSpec in infrastructure/agents/cli/ and adding one line here - no
changes anywhere else in the codebase.
"""

from __future__ import annotations

from typing import Callable

from cvpal.domain.ports.text_completion import TextCompletionPort
from cvpal.infrastructure.agents.cli.claude_code import CLAUDE_CODE
from cvpal.infrastructure.agents.cli.opencode import OPENCODE
from cvpal.infrastructure.agents.cli_adapter import CliAgentAdapter

_FACTORIES: dict[str, Callable[[], TextCompletionPort]] = {
    "opencode": lambda: CliAgentAdapter(OPENCODE),
    "claude-code": lambda: CliAgentAdapter(CLAUDE_CODE),
}


def available_agents() -> list[str]:
    return sorted(_FACTORIES)


def build_agent(name: str) -> TextCompletionPort:
    try:
        factory = _FACTORIES[name]
    except KeyError:
        raise ValueError(
            f"Unknown agent '{name}'. Available: {', '.join(available_agents())}"
        ) from None
    return factory()
