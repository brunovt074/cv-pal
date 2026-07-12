from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import typer
from dotenv import load_dotenv

from cvpal.analytics.cover_letters import build_cover_letters
from cvpal.analytics.cv_versions import build_cv_versions
from cvpal.analytics.structure import structure_knowledge_base
from cvpal.ingest import ingest_all
from cvpal.ingest.models import RawDocument
from cvpal.knowledge.workbook import build_workbook

load_dotenv()

app = typer.Typer(help="CV-Pal: knowledge base + tailored CV/cover-letter generation")

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DIR = Path(os.environ.get("CV_RAW_DIR", "/home/br1/cv"))
INGEST_OUTPUT = REPO_ROOT / "data" / "ingested.json"
WORKBOOK_OUTPUT = REPO_ROOT / "data" / "cv-knowledge-base.xlsx"
CHECKPOINT_DIR = REPO_ROOT / "data" / ".checkpoints"


@app.command()
def ingest(
    raw_dir: Path = typer.Option(DEFAULT_RAW_DIR, help="Root directory of source CV/cover-letter files"),
    output: Path = typer.Option(INGEST_OUTPUT, help="Where to write the normalized JSON dump"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Parse all source documents into normalized JSON records."""
    logging.basicConfig(level=logging.INFO if verbose else logging.WARNING)

    documents = ingest_all(raw_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps([doc.model_dump() for doc in documents], indent=2, ensure_ascii=False)
    )

    total = len(documents)
    cvs = sum(1 for d in documents if d.doc_kind == "cv")
    letters = sum(1 for d in documents if d.doc_kind == "cover_letter")
    with_warnings = sum(1 for d in documents if d.extraction_warnings)
    unknown_lang = sum(1 for d in documents if d.source_language == "unknown")

    typer.echo(f"Ingested {total} documents ({cvs} CVs, {letters} cover letters) -> {output}")
    typer.echo(f"  {with_warnings} documents had extraction warnings")
    typer.echo(f"  {unknown_lang} documents had undetected language")


@app.command("build-sheet")
def build_sheet(
    raw_dir: Path = typer.Option(DEFAULT_RAW_DIR, help="Root directory of source CV/cover-letter files"),
    ingested_json: Path = typer.Option(
        INGEST_OUTPUT, help="Pre-ingested JSON to reuse instead of re-parsing all source files"
    ),
    output: Path = typer.Option(WORKBOOK_OUTPUT, help="Where to write the knowledge base workbook"),
    checkpoint_dir: Path = typer.Option(
        CHECKPOINT_DIR, help="Where to cache each LLM step's result so a killed/rerun invocation resumes"
    ),
) -> None:
    """Build data/cv-knowledge-base.xlsx from ingested documents.

    Reuses `ingested_json` if it exists (avoids re-parsing 48 files just to
    re-run the structuring/translation LLM step); pass a raw_dir with no
    existing ingested.json to force a fresh ingest.

    Each LLM structuring step is checkpointed under `checkpoint_dir` - safe
    to re-run this command after a timeout/interruption, it will skip any
    step that already has a checkpoint file instead of re-calling the LLM.
    """
    if ingested_json.exists():
        typer.echo(f"Reusing existing ingestion at {ingested_json}")
        documents = [RawDocument(**d) for d in json.loads(ingested_json.read_text())]
    else:
        typer.echo(f"No ingestion found, running ingest against {raw_dir}...")
        documents = ingest_all(raw_dir)
        ingested_json.parent.mkdir(parents=True, exist_ok=True)
        ingested_json.write_text(
            json.dumps([doc.model_dump() for doc in documents], indent=2, ensure_ascii=False)
        )

    typer.echo(f"Structuring + translating knowledge base (checkpoints in {checkpoint_dir})...")
    knowledge_base = structure_knowledge_base(documents, checkpoint_dir=checkpoint_dir)

    typer.echo("Building CVVersions inventory...")
    cv_versions = build_cv_versions(documents, raw_dir)

    typer.echo("Translating cover letters (calls the LLM)...")
    cover_letters = build_cover_letters(documents, checkpoint_dir=checkpoint_dir)

    build_workbook(knowledge_base, cv_versions, cover_letters, output)

    typer.echo(f"Wrote knowledge base workbook -> {output}")
    typer.echo(f"  {len(knowledge_base.experience)} experience bullets")
    typer.echo(f"  {len(knowledge_base.skills)} skills")
    typer.echo(f"  {len(knowledge_base.education)} education entries")
    typer.echo(f"  {len(cv_versions)} CV versions tracked")
    typer.echo(f"  {len(cover_letters)} cover letters translated")


if __name__ == "__main__":
    app()
