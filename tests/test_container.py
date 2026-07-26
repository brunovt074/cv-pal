from __future__ import annotations

from pathlib import Path

import pytest

from cvpal.config import Settings
from cvpal.container import Container
from cvpal.domain.capabilities import Capability
from cvpal.domain.errors import CapabilityNotSupportedError
from cvpal.infrastructure.job_postings.url_source import UrlJobPostingSource
from cvpal.infrastructure.web_content.http_web_content import HttpWebContent


def _settings(agent_name: str) -> Settings:
    settings = Settings(config_path=Path("/nonexistent/cvpal-test-config.toml"))
    settings.agent_name = agent_name
    return settings


def test_require_returns_agent_when_capability_supported():
    container = Container(_settings("opencode"))
    agent = container.require(Capability.TEXT_COMPLETION)
    assert agent is container.agent


def test_require_raises_when_capability_missing():
    container = Container(_settings("opencode"))
    with pytest.raises(CapabilityNotSupportedError):
        container.require(Capability.DOCUMENT_RENDER)


def test_agent_is_built_once_and_cached():
    container = Container(_settings("opencode"))
    first = container.agent
    second = container.agent
    assert first is second


def test_job_posting_source_wires_a_real_web_content_port_for_urls():
    container = Container(_settings("opencode"))
    source = container.job_posting_source(url="https://example.com/job")
    assert isinstance(source, UrlJobPostingSource)
    assert isinstance(container.web_content, HttpWebContent)
