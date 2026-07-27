from __future__ import annotations

import subprocess

from cvpal.domain.errors import AgentUnavailableError


def run_process(argv: list[str], *, timeout: int) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise AgentUnavailableError(f"Binary not found: {argv[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise AgentUnavailableError(
            f"Process timed out after {timeout}s: {argv[0]}"
        ) from exc
