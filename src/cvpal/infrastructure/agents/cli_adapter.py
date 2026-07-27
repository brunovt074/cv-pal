from __future__ import annotations

import os

from cvpal.domain.errors import InvalidAgentResponseError
from cvpal.domain.ports.text_completion import CompletionRequest, CompletionResult
from cvpal.infrastructure.agents.process_runner import run_process
from cvpal.infrastructure.agents.spec import CliAgentSpec


class CliAgentAdapter:
    """Generic TextCompletionPort implementation for any CliAgentSpec.

    This is the entire mechanism that makes cv-pal agent-agnostic: every
    subprocess-based provider (opencode, Claude Code, Codex, ...) is one
    spec, not one adapter class.
    """

    def __init__(self, spec: CliAgentSpec) -> None:
        self._spec = spec
        self.capabilities = spec.capabilities
        self._binary = os.environ.get(spec.binary_env_var, spec.default_binary)
        self._model = os.environ.get(spec.model_env_var, spec.default_model)

    @property
    def name(self) -> str:
        return self._spec.name

    def complete(self, request: CompletionRequest) -> CompletionResult:
        argv = [self._binary, *self._spec.build_argv(request, self._model)]
        result = run_process(argv, timeout=self._spec.timeout_seconds)

        if result.returncode != 0:
            raise InvalidAgentResponseError(
                self._spec.name,
                f"exit code {result.returncode}: {result.stderr[:2000]}",
                raw_response=result.stdout[-2000:],
            )

        text = self._spec.parse_stdout(result.stdout)
        if not text:
            raise InvalidAgentResponseError(
                self._spec.name,
                "produced no text output (it may have attempted a denied tool call)",
                raw_response=result.stdout[-2000:],
            )
        return CompletionResult(text=text)
