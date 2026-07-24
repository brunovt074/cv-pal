from __future__ import annotations

import pytest

from cvpal.domain.capabilities import Capability
from cvpal.infrastructure.agents.cli_adapter import CliAgentAdapter
from cvpal.infrastructure.agents.registry import available_agents, build_agent


def test_available_agents_lists_registered_providers():
    assert available_agents() == ["claude-code", "opencode"]


def test_build_agent_returns_cli_adapter_for_opencode():
    agent = build_agent("opencode")
    assert isinstance(agent, CliAgentAdapter)
    assert Capability.TEXT_COMPLETION in agent.capabilities


def test_build_agent_returns_cli_adapter_for_claude_code():
    agent = build_agent("claude-code")
    assert isinstance(agent, CliAgentAdapter)
    assert Capability.JSON_COMPLETION in agent.capabilities


def test_build_agent_raises_on_unknown_name():
    with pytest.raises(ValueError, match="Unknown agent"):
        build_agent("does-not-exist")
