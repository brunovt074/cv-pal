from __future__ import annotations

from pathlib import Path

import pytest

from cvpal.config import Settings

_NO_CONFIG = Path("/nonexistent/cvpal-test-config.toml")


def test_defaults_to_placeholder_identity_when_no_config_file_or_env(monkeypatch):
    for var in ("CVPAL_USER_NAME", "CVPAL_USER_SLUG", "CVPAL_PHONE", "CVPAL_LINKEDIN", "CVPAL_GITHUB", "CVPAL_AGENT", "CV_RAW_DIR", "CV_DATA_DIR"):
        monkeypatch.delenv(var, raising=False)

    settings = Settings(config_path=_NO_CONFIG)

    assert settings.user.name == "Alex Doe"
    assert settings.user.slug == "alex-doe"
    assert settings.user.default_language == "en"
    assert settings.user.preferred_values["phone"] == "+1-555-0100"
    assert settings.agent_name == "opencode"
    assert settings.raw_dir == Path("./cv-raw")


def test_reads_values_from_config_file(tmp_path, monkeypatch):
    for var in ("CVPAL_USER_NAME", "CVPAL_USER_SLUG", "CVPAL_PHONE", "CV_RAW_DIR", "CV_DATA_DIR"):
        monkeypatch.delenv(var, raising=False)

    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """\
[user]
name = "Jordan Smith"
slug = "jordan-smith"
default_language = "es"

[user.preferred_values]
phone = "+1-555-9999"
linkedin = "https://www.linkedin.com/in/jordan-smith-dev/"
github = "jordansmith"

[paths]
raw_dir = "/tmp/jordan-cvs"

[agent]
provider = "claude-code"
"""
    )

    settings = Settings(config_path=config_file)

    assert settings.user.name == "Jordan Smith"
    assert settings.user.slug == "jordan-smith"
    assert settings.user.default_language == "es"
    assert settings.user.preferred_values["phone"] == "+1-555-9999"
    assert settings.agent_name == "claude-code"
    assert settings.raw_dir == Path("/tmp/jordan-cvs")


def test_env_var_overrides_config_file(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """\
[user]
name = "Jordan Smith"
slug = "jordan-smith"
"""
    )
    monkeypatch.setenv("CVPAL_USER_SLUG", "env-wins")

    settings = Settings(config_path=config_file)

    assert settings.user.name == "Jordan Smith"  # from config file, no env override
    assert settings.user.slug == "env-wins"  # env var wins over config file


def test_default_language_env_var_overrides_config_file(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    config_file.write_text('[user]\ndefault_language = "es"\n')
    monkeypatch.setenv("CVPAL_DEFAULT_LANGUAGE", "fr")

    settings = Settings(config_path=config_file)

    assert settings.user.default_language == "fr"


def test_missing_config_file_does_not_raise(tmp_path):
    settings = Settings(config_path=tmp_path / "does-not-exist.toml")
    assert settings.user.name == "Alex Doe"


@pytest.mark.parametrize("var", ["CV_RAW_DIR", "CV_DATA_DIR"])
def test_path_env_vars_expand_user(tmp_path, monkeypatch, var):
    monkeypatch.setenv(var, "~/some-cvpal-dir")
    settings = Settings(config_path=_NO_CONFIG)
    attr = "raw_dir" if var == "CV_RAW_DIR" else "data_dir"
    assert str(getattr(settings, attr)).startswith(str(Path.home()))
