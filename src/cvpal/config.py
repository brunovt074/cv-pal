from __future__ import annotations

import os
import tomllib
from pathlib import Path

from cvpal.domain.user.profile import UserProfile

REPO_ROOT = Path(__file__).resolve().parents[2]


def _xdg_dir(env_var: str, default_base: str, leaf: str) -> Path:
    base = os.environ.get(env_var, default_base)
    return Path(base).expanduser() / leaf


def default_config_file() -> Path:
    return _xdg_dir("XDG_CONFIG_HOME", "~/.config", "cvpal") / "config.toml"


def default_data_dir() -> Path:
    return _xdg_dir("XDG_DATA_HOME", "~/.local/share", "cvpal")


def _load_config_file(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        return tomllib.load(handle)


class Settings:
    """Runtime configuration.

    Precedence, highest first: environment variable > `config_file`
    (~/.config/cvpal/config.toml by default) > built-in placeholder
    identity/paths. `.env` is loaded once via python-dotenv at the CLI
    entry point, before this is constructed, so env vars there apply too.

    `config_path` is only ever overridden by tests, to point at a
    tmp_path fixture instead of the real machine's config file - letting
    the default stay a no-arg `Settings()` for every real caller.
    """

    def __init__(self, *, config_path: Path | None = None) -> None:
        self.config_file: Path = config_path or default_config_file()
        config = _load_config_file(self.config_file)

        user_section: dict = config.get("user", {})
        preferred: dict = user_section.get("preferred_values", {})
        default_user = UserProfile()
        self.user = UserProfile(
            name=os.environ.get("CVPAL_USER_NAME", user_section.get("name", default_user.name)),
            slug=os.environ.get("CVPAL_USER_SLUG", user_section.get("slug", default_user.slug)),
            preferred_values={
                "phone": os.environ.get(
                    "CVPAL_PHONE", preferred.get("phone", default_user.preferred_values["phone"])
                ),
                "linkedin": os.environ.get(
                    "CVPAL_LINKEDIN",
                    preferred.get("linkedin", default_user.preferred_values["linkedin"]),
                ),
                "github": os.environ.get(
                    "CVPAL_GITHUB", preferred.get("github", default_user.preferred_values["github"])
                ),
            },
        )

        agent_section: dict = config.get("agent", {})
        self.agent_name: str = os.environ.get("CVPAL_AGENT", agent_section.get("provider", "opencode"))

        paths_section: dict = config.get("paths", {})

        raw_dir_value = os.environ.get("CV_RAW_DIR") or paths_section.get("raw_dir")
        self.raw_dir: Path = Path(raw_dir_value).expanduser() if raw_dir_value else Path("./cv-raw")

        data_dir_value = os.environ.get("CV_DATA_DIR") or paths_section.get("data_dir")
        self.data_dir: Path = Path(data_dir_value).expanduser() if data_dir_value else default_data_dir()

        self.ingested_json: Path = self.data_dir / "ingested.json"
        self.knowledge_base_md: Path = self.data_dir / "knowledge-base.md"
        self.workbook_xlsx: Path = self.data_dir / "cv-knowledge-base.xlsx"
        self.checkpoint_dir: Path = self.data_dir / ".checkpoints"
        self.outputs_dir: Path = self.data_dir / "outputs"


def get_settings() -> Settings:
    return Settings()
