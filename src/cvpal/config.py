from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings:
    """Runtime configuration, read from environment (.env via python-dotenv,
    loaded once at the interfaces/cli entry point).
    """

    def __init__(self) -> None:
        self.agent_name: str = os.environ.get("CVPAL_AGENT", "opencode")
        self.raw_dir: Path = Path(os.environ.get("CV_RAW_DIR", "/home/br1/cv"))
        self.data_dir: Path = REPO_ROOT / "data"
        self.ingested_json: Path = self.data_dir / "ingested.json"
        self.knowledge_base_md: Path = self.data_dir / "knowledge-base.md"
        self.workbook_xlsx: Path = self.data_dir / "cv-knowledge-base.xlsx"
        self.checkpoint_dir: Path = self.data_dir / ".checkpoints"
        self.outputs_dir: Path = self.data_dir / "outputs"


def get_settings() -> Settings:
    return Settings()
