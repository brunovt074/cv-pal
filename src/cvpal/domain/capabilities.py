from __future__ import annotations

from enum import Enum


class Capability(str, Enum):
    """What an agent adapter can actually do.

    Declared per-adapter (see infrastructure/agents/) and checked by
    container.py when wiring a use case to a provider — a use case that
    needs DOCUMENT_RENDER must fail at startup against an agent that only
    has TEXT_COMPLETION, not four minutes into a pipeline run.
    """

    TEXT_COMPLETION = "text_completion"
    JSON_COMPLETION = "json_completion"
    DOCUMENT_RENDER = "document_render"
    WEB_CONTENT = "web_content"
    FILE_ATTACH = "file_attach"
