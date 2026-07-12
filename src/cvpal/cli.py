from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import typer
from dotenv import load_dotenv

from cvpal.ingest import ingest_all

load_dotenv()

app = typer.Typer(help="CV-Pal: knowledge base + tailored CV/cover-letter generation")

DEFAULT_RAW_DIR = Path(os.environ.get("CV_RAW_DIR", "/home/br1/cv"))
INGEST_OUTPUT = Path(__file__).resolve().parents[2] / "data" / "ingested.json"


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


if __name__ == "__main__":
    app()
