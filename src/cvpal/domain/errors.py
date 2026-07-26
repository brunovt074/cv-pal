from __future__ import annotations

from cvpal.domain.capabilities import Capability


class CvPalError(Exception):
    pass


class CapabilityNotSupportedError(CvPalError):
    def __init__(self, agent_name: str, capability: Capability) -> None:
        self.agent_name = agent_name
        self.capability = capability
        super().__init__(
            f"Agent '{agent_name}' does not support capability '{capability.value}'"
        )


class AgentUnavailableError(CvPalError):
    pass


class InvalidAgentResponseError(CvPalError):
    def __init__(self, agent_name: str, detail: str, raw_response: str = "") -> None:
        self.agent_name = agent_name
        self.raw_response = raw_response
        super().__init__(f"Agent '{agent_name}' returned an invalid response: {detail}")


class KnowledgeBaseNotFoundError(CvPalError):
    pass


class DocumentRenderError(CvPalError):
    pass


class JobPostingFetchError(CvPalError):
    def __init__(self, url: str, detail: str) -> None:
        self.url = url
        super().__init__(f"Failed to fetch job posting from '{url}': {detail}")
