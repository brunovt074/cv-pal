from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from cvpal.domain.capabilities import Capability


@dataclass(frozen=True)
class CompletionRequest:
    prompt: str
    expects_json: bool = False


@dataclass(frozen=True)
class CompletionResult:
    text: str


class TextCompletionPort(Protocol):
    """Text-in/text-out generation: translation, structuring, extraction.

    Every agent adapter (opencode, Claude Code, Anthropic SDK, ...)
    implements this — it's the one capability every provider is assumed
    to have. `capabilities` lets container.py verify a use case's other
    requirements (DOCUMENT_RENDER, WEB_CONTENT) before wiring it.
    """

    capabilities: frozenset[Capability]

    def complete(self, request: CompletionRequest) -> CompletionResult: ...
