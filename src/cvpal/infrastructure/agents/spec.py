"""Declarative shape for a CLI-driven agent adapter.

The pattern behind opencode, Claude Code, Codex, and Gemini CLI is the
same: launch a binary with a prompt, parse its stdout. Adding a new
provider means writing one CliAgentSpec + a parser function - zero changes
to CliAgentAdapter, the registry, or any use case. See
infrastructure/agents/cli/opencode.py and cli/claude_code.py for concrete
specs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from cvpal.domain.capabilities import Capability
from cvpal.domain.ports.text_completion import CompletionRequest


@dataclass(frozen=True)
class CliAgentSpec:
    name: str
    default_binary: str
    binary_env_var: str
    default_model: str
    model_env_var: str
    build_argv: Callable[[CompletionRequest, str], list[str]]
    parse_stdout: Callable[[str], str]
    capabilities: frozenset[Capability]
    timeout_seconds: int = 600
