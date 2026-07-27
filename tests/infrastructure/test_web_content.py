from __future__ import annotations

import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from cvpal.domain.errors import JobPostingFetchError
from cvpal.infrastructure.web_content.http_web_content import HttpWebContent, _html_to_text


def _fake_response(html: str, charset: str = "utf-8"):
    response = MagicMock()
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    response.read.return_value = html.encode(charset)
    response.headers.get_content_charset.return_value = charset
    return response


def test_html_to_text_strips_tags_scripts_and_styles():
    html = """
    <html><head><style>.x{color:red}</style></head>
    <body>
      <script>console.log('x')</script>
      <h1>Backend Developer</h1>
      <p>We need <b>Java</b> and Spring Boot experience.</p>
    </body></html>
    """
    text = _html_to_text(html)
    assert "Backend Developer" in text
    assert "Java" in text
    assert "Spring Boot experience." in text
    assert "console.log" not in text
    assert "color:red" not in text


def test_fetch_returns_readable_text():
    html = "<html><body><p>Senior Backend Engineer, remote.</p></body></html>"
    with patch("urllib.request.urlopen", return_value=_fake_response(html)):
        text = HttpWebContent().fetch("https://example.com/job")
    assert text == "Senior Backend Engineer, remote."


def test_fetch_raises_job_posting_fetch_error_on_network_failure():
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
        with pytest.raises(JobPostingFetchError) as exc_info:
            HttpWebContent().fetch("https://example.com/job")
    assert exc_info.value.url == "https://example.com/job"


def test_fetch_raises_job_posting_fetch_error_when_page_has_no_readable_text():
    html = "<html><head><script>onlyJs()</script></head><body></body></html>"
    with patch("urllib.request.urlopen", return_value=_fake_response(html)):
        with pytest.raises(JobPostingFetchError):
            HttpWebContent().fetch("https://example.com/job")
