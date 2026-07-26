"""Composition root — the only module allowed to import both `domain` and
`infrastructure` and wire them together. Use cases and interfaces never
import an infrastructure adapter directly; they ask the container.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from cvpal.config import Settings, get_settings
from cvpal.domain.capabilities import Capability
from cvpal.domain.errors import CapabilityNotSupportedError
from cvpal.domain.knowledge.models import KnowledgeBase
from cvpal.domain.ports.job_posting_source import JobPostingSourcePort
from cvpal.domain.ports.text_completion import TextCompletionPort
from cvpal.domain.ports.web_content import WebContentPort
from cvpal.infrastructure.agents.registry import available_agents, build_agent
from cvpal.infrastructure.job_postings.file_source import FileJobPostingSource
from cvpal.infrastructure.job_postings.text_source import InlineTextJobPostingSource
from cvpal.infrastructure.job_postings.url_source import UrlJobPostingSource
from cvpal.infrastructure.parsers.dispatch import MultiFormatDocumentParser
from cvpal.infrastructure.parsers.sections import detect_language
from cvpal.infrastructure.persistence.file_checkpoint_store import FileCheckpointStore
from cvpal.infrastructure.persistence.json_raw_document_repository import (
    JsonRawDocumentRepository,
)
from cvpal.infrastructure.persistence.markdown_knowledge_repository import (
    MarkdownKnowledgeRepository,
    parse_markdown,
)
from cvpal.infrastructure.rendering.local_document_renderer import LocalDocumentRenderer
from cvpal.infrastructure.web_content.http_web_content import HttpWebContent


class Container:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._agent: TextCompletionPort | None = None

    @property
    def agent(self) -> TextCompletionPort:
        if self._agent is None:
            self._agent = build_agent(self.settings.agent_name)
        return self._agent

    @staticmethod
    def available_agents() -> list[str]:
        return available_agents()

    def require(self, *capabilities: Capability) -> TextCompletionPort:
        """Return the configured agent, or raise CapabilityNotSupportedError
        immediately if it can't do everything the caller needs - fail at
        wiring time, not mid-pipeline.
        """
        agent = self.agent
        for capability in capabilities:
            if capability not in agent.capabilities:
                raise CapabilityNotSupportedError(self.settings.agent_name, capability)
        return agent

    @property
    def document_parser(self) -> MultiFormatDocumentParser:
        return MultiFormatDocumentParser()

    @property
    def raw_document_repository(self) -> JsonRawDocumentRepository:
        return JsonRawDocumentRepository(self.settings.ingested_json)

    @property
    def knowledge_repository(self) -> MarkdownKnowledgeRepository:
        return MarkdownKnowledgeRepository(
            self.settings.knowledge_base_md, header_name=self.settings.user.name
        )

    @property
    def checkpoint_store(self) -> FileCheckpointStore:
        return FileCheckpointStore(self.settings.checkpoint_dir)

    @property
    def detect_language(self) -> Callable[[str], str]:
        return detect_language

    @property
    def parse_knowledge_base_markdown(self) -> Callable[[str], KnowledgeBase]:
        return parse_markdown

    @property
    def document_renderer(self) -> LocalDocumentRenderer:
        return LocalDocumentRenderer()

    @property
    def web_content(self) -> WebContentPort:
        return HttpWebContent()

    def job_posting_source(
        self, *, text: str | None = None, file: Path | None = None, url: str | None = None
    ) -> JobPostingSourcePort:
        provided = [v for v in (text, file, url) if v is not None]
        if len(provided) != 1:
            raise ValueError("Provide exactly one of: text, file, url")
        if text is not None:
            return InlineTextJobPostingSource(text)
        if file is not None:
            return FileJobPostingSource(file)
        return UrlJobPostingSource(url, web_content=self.web_content)
