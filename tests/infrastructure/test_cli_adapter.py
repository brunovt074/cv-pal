from __future__ import annotations

import subprocess

import pytest

from cvpal.domain.capabilities import Capability
from cvpal.domain.errors import InvalidAgentResponseError
from cvpal.domain.ports.text_completion import CompletionRequest
from cvpal.infrastructure.agents.cli_adapter import CliAgentAdapter
from cvpal.infrastructure.agents.spec import CliAgentSpec

RUN_PROCESS_PATH = "cvpal.infrastructure.agents.cli_adapter.run_process"


def _make_spec(build_argv=None, parse_stdout=None) -> CliAgentSpec:
    return CliAgentSpec(
        name="fake",
        default_binary="fake-bin",
        binary_env_var="FAKE_BIN",
        default_model="fake-model",
        model_env_var="FAKE_MODEL",
        build_argv=build_argv or (lambda req, model: ["run", req.prompt]),
        parse_stdout=parse_stdout or (lambda out: out.strip()),
        capabilities=frozenset({Capability.TEXT_COMPLETION}),
    )


def test_complete_returns_parsed_text(monkeypatch):
    adapter = CliAgentAdapter(_make_spec())

    def fake_run_process(argv, *, timeout):
        assert argv == ["fake-bin", "run", "hello"]
        return subprocess.CompletedProcess(argv, 0, stdout="hello world\n", stderr="")

    monkeypatch.setattr(RUN_PROCESS_PATH, fake_run_process)
    result = adapter.complete(CompletionRequest(prompt="hello"))
    assert result.text == "hello world"


def test_complete_raises_on_nonzero_exit(monkeypatch):
    adapter = CliAgentAdapter(_make_spec())
    monkeypatch.setattr(
        RUN_PROCESS_PATH,
        lambda argv, *, timeout: subprocess.CompletedProcess(argv, 1, stdout="", stderr="boom"),
    )
    with pytest.raises(InvalidAgentResponseError):
        adapter.complete(CompletionRequest(prompt="hello"))


def test_complete_raises_on_empty_response(monkeypatch):
    adapter = CliAgentAdapter(_make_spec(parse_stdout=lambda out: ""))
    monkeypatch.setattr(
        RUN_PROCESS_PATH,
        lambda argv, *, timeout: subprocess.CompletedProcess(argv, 0, stdout="", stderr=""),
    )
    with pytest.raises(InvalidAgentResponseError):
        adapter.complete(CompletionRequest(prompt="hello"))


def test_env_overrides_binary_and_model(monkeypatch):
    monkeypatch.setenv("FAKE_BIN", "custom-bin")
    monkeypatch.setenv("FAKE_MODEL", "custom-model")

    def build_argv(request, model):
        return ["run", model]

    def fake_run_process(argv, *, timeout):
        assert argv[0] == "custom-bin"
        assert argv[-1] == "custom-model"
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    adapter = CliAgentAdapter(_make_spec(build_argv=build_argv))
    monkeypatch.setattr(RUN_PROCESS_PATH, fake_run_process)
    result = adapter.complete(CompletionRequest(prompt="x"))
    assert result.text == "ok"
