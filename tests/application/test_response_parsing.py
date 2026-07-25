import pytest

from cvpal.domain.errors import InvalidAgentResponseError
from cvpal.application.services.response_parsing import (
    parse_json_response,
    strip_markdown_fence,
)


def test_parse_json_response_plain_object():
    assert parse_json_response("fake", '{"a": 1}') == {"a": 1}


def test_parse_json_response_plain_list():
    assert parse_json_response("fake", "[1, 2, 3]") == [1, 2, 3]


def test_parse_json_response_strips_markdown_fence():
    text = "```json\n[1, 2]\n```"
    assert parse_json_response("fake", text) == [1, 2]


def test_parse_json_response_tolerates_trailing_prose():
    text = '[{"a": 1}]\n\nNote: this is a summary of the extracted skills.'
    assert parse_json_response("fake", text) == [{"a": 1}]


def test_parse_json_response_tolerates_trailing_blank_lines_and_fence():
    text = '{"a": 1}\n\n```\nignored trailing fence\n```'
    assert parse_json_response("fake", text) == {"a": 1}


def test_parse_json_response_raises_on_garbage():
    with pytest.raises(InvalidAgentResponseError):
        parse_json_response("fake", "not json at all")


def test_strip_markdown_fence_no_fence_passthrough():
    assert strip_markdown_fence("  [1, 2]  ") == "[1, 2]"
