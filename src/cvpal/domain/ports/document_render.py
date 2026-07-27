from __future__ import annotations

from pathlib import Path
from typing import Protocol

from cvpal.domain.generation.models import DocumentFormat


class DocumentRenderPort(Protocol):
    """Renders text content into a real .docx/.pdf file.

    Not every agent can do this (opencode's non-interactive `run` mode has
    no equivalent to Anthropic's Agent Skills + code execution container)
    — see skills/cv-generation/SKILL.md. Adapters that can't implement this
    simply aren't registered for it; container.py raises
    CapabilityNotSupportedError at wiring time if a use case needs it.
    """

    def render(self, content: str, *, document_format: DocumentFormat, output_path: Path) -> Path: ...
