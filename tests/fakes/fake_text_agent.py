from __future__ import annotations

from cvpal.domain.capabilities import Capability
from cvpal.domain.ports.text_completion import CompletionRequest, CompletionResult


class FakeTextAgent:
    """Scripted TextCompletionPort for use-case tests — no subprocess, no
    network. Responses are returned in order, one per `complete()` call.
    """

    def __init__(
        self,
        responses: list[str],
        capabilities: frozenset[Capability] | None = None,
    ) -> None:
        self.capabilities = capabilities or frozenset(
            {Capability.TEXT_COMPLETION, Capability.JSON_COMPLETION}
        )
        self._responses = list(responses)
        self.requests: list[CompletionRequest] = []

    def complete(self, request: CompletionRequest) -> CompletionResult:
        self.requests.append(request)
        if not self._responses:
            raise AssertionError("FakeTextAgent ran out of scripted responses")
        return CompletionResult(text=self._responses.pop(0))
