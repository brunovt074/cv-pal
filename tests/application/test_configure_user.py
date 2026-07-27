from cvpal.application.use_cases.configure_user import write_user_config


def test_write_user_config_creates_file_with_given_fields(tmp_path):
    config_file = tmp_path / "config.toml"

    write_user_config(
        config_file,
        name="Jordan Smith",
        slug="jordan-smith",
        default_language="es",
        phone="+1-555-9999",
        linkedin="https://www.linkedin.com/in/jordan-smith-dev/",
        github="jordansmith",
        raw_dir="/tmp/jordan-cvs",
        provider="claude-code",
    )

    text = config_file.read_text()
    assert 'name = "Jordan Smith"' in text
    assert 'slug = "jordan-smith"' in text
    assert 'default_language = "es"' in text
    assert 'phone = "+1-555-9999"' in text
    assert 'raw_dir = "/tmp/jordan-cvs"' in text
    assert 'provider = "claude-code"' in text


def test_write_user_config_merges_into_existing_file_without_clobbering_other_fields(tmp_path):
    config_file = tmp_path / "config.toml"
    write_user_config(config_file, name="Jordan Smith", raw_dir="/tmp/cvs")

    write_user_config(config_file, default_language="es")

    text = config_file.read_text()
    assert 'name = "Jordan Smith"' in text  # untouched by the second call
    assert 'raw_dir = "/tmp/cvs"' in text  # untouched by the second call
    assert 'default_language = "es"' in text


def test_write_user_config_only_writes_provided_fields_leaves_rest_absent(tmp_path):
    config_file = tmp_path / "config.toml"

    write_user_config(config_file, raw_dir="/tmp/cvs")

    text = config_file.read_text()
    assert "raw_dir" in text
    assert "name" not in text
    assert "[agent]" not in text


def test_write_user_config_escapes_quotes_and_backslashes(tmp_path):
    config_file = tmp_path / "config.toml"

    write_user_config(config_file, name='Jane "JJ" O\\Brien')

    text = config_file.read_text()
    assert 'name = "Jane \\"JJ\\" O\\\\Brien"' in text


def test_write_user_config_returns_the_resulting_config_dict(tmp_path):
    config_file = tmp_path / "config.toml"

    result = write_user_config(config_file, name="Jordan Smith", raw_dir="/tmp/cvs")

    assert result["user"]["name"] == "Jordan Smith"
    assert result["paths"]["raw_dir"] == "/tmp/cvs"
