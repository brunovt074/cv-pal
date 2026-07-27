from __future__ import annotations

import json

from cvpal.infrastructure.agents.cli.claude_code import _parse_stdout


def test_parse_stdout_extracts_result_field():
    stdout = json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "hi"})
    assert _parse_stdout(stdout) == "hi"


def test_parse_stdout_returns_empty_on_error_flag():
    stdout = json.dumps({"type": "result", "is_error": True, "result": "partial"})
    assert _parse_stdout(stdout) == ""


def test_parse_stdout_returns_empty_on_invalid_json():
    assert _parse_stdout("not json") == ""


def test_parse_stdout_returns_empty_on_blank_input():
    assert _parse_stdout("   ") == ""
