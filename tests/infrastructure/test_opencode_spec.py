from __future__ import annotations

import json

from cvpal.infrastructure.agents.cli.opencode import _parse_stdout


def _event(part_id: str, text: str) -> str:
    return json.dumps({"type": "text", "part": {"id": part_id, "text": text}})


def test_parse_stdout_concatenates_text_events():
    stdout = "\n".join([_event("a", "Hello "), _event("b", "world")])
    assert _parse_stdout(stdout) == "Hello world"


def test_parse_stdout_dedupes_repeated_part_id():
    stdout = "\n".join(
        [_event("a", "Hello"), _event("a", "Hello"), _event("b", " world")]
    )
    assert _parse_stdout(stdout) == "Hello world"


def test_parse_stdout_ignores_non_text_events_and_garbage_lines():
    stdout = "\n".join(
        [
            json.dumps({"type": "tool_call", "part": {"id": "x", "text": "ignored"}}),
            "not json at all",
            "",
            _event("a", "kept"),
        ]
    )
    assert _parse_stdout(stdout) == "kept"


def test_parse_stdout_empty_input_returns_empty_string():
    assert _parse_stdout("") == ""
