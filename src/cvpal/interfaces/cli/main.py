from __future__ import annotations

import logging
from pathlib import Path

import typer
from dotenv import load_dotenv

from cvpal.application.use_cases.audit_knowledge_base import audit_personal_data
from cvpal.application.use_cases.build_knowledge_base import build_knowledge_base
from cvpal.application.use_cases.ingest_documents import ingest_documents
from cvpal.application.use_cases.tailor_cv import tailor_cv
from cvpal.config import get_settings
from cvpal.container import Container
from cvpal.domain.capabilities import Capability
from cvpal.domain.errors import DocumentRenderError
from cvpal.domain.generation.models import DocumentFormat
from cvpal.domain.ports.text_completion import CompletionRequest

load_dotenv()

app = typer.Typer(help="CV-Pal: knowledge base + tailored CV/cover-letter generation")
agents_app = typer.Typer(help="Inspect/verify the configured text-completion agent")
kb_app = typer.Typer(help="Build/inspect the knowledge base (data/knowledge-base.md)")
app.add_typer(agents_app, name="agents")
app.add_typer(kb_app, name="kb")


@app.command()
def ingest(
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Parse all source documents (CV_RAW_DIR) into normalized JSON.

    Skips re-parsing a file whose mtime/size match the previous ingest -
    only new/changed files pay the extraction cost.
    """
    logging.basicConfig(level=logging.INFO if verbose else logging.WARNING)
    settings = get_settings()
    container = Container(settings)

    previous = (
        container.raw_document_repository.load()
        if container.raw_document_repository.exists()
        else None
    )
    result = ingest_documents(settings.raw_dir, container.document_parser, previous=previous)
    container.raw_document_repository.save(result.documents)

    documents = result.documents
    total = len(documents)
    cvs = sum(1 for d in documents if d.doc_kind == "cv")
    letters = sum(1 for d in documents if d.doc_kind == "cover_letter")
    with_warnings = sum(1 for d in documents if d.extraction_warnings)
    unknown_lang = sum(1 for d in documents if d.source_language == "unknown")

    typer.echo(f"Ingested {total} documents ({cvs} CVs, {letters} cover letters) -> {settings.ingested_json}")
    typer.echo(f"  {result.reused_count} unchanged (skipped), {result.reparsed_count} parsed")
    typer.echo(f"  {with_warnings} documents had extraction warnings")
    typer.echo(f"  {unknown_lang} documents had undetected language")


@kb_app.command("build")
def kb_build(
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Bootstrap/refresh data/knowledge-base.md from data/ingested.json.

    Runs one agent call per canonical section (JSON, validated against
    domain models) and one for the voice profile. Each section is
    checkpointed by a fingerprint of its own input under data/.checkpoints/,
    so a section whose underlying CVs haven't changed costs zero agent
    calls - safe to re-run any time, not just when adding new CVs.
    """
    logging.basicConfig(level=logging.INFO if verbose else logging.WARNING)
    settings = get_settings()
    container = Container(settings)

    if not container.raw_document_repository.exists():
        typer.echo("No ingestion found. Run `cvpal ingest` first.", err=True)
        raise typer.Exit(1)

    agent = container.require(Capability.TEXT_COMPLETION, Capability.JSON_COMPLETION)
    documents = container.raw_document_repository.load()

    typer.echo(f"Building knowledge base with agent '{settings.agent_name}'...")
    report = build_knowledge_base(documents, agent, settings.agent_name, container.checkpoint_store)
    knowledge_base = report.knowledge_base
    container.knowledge_repository.save(knowledge_base)

    if report.rebuilt_sections:
        typer.echo(f"  rebuilt: {', '.join(report.rebuilt_sections)}")
    else:
        typer.echo("  up to date - no section changed, zero agent calls made")
    if report.skipped_sections:
        typer.echo(f"  unchanged (skipped): {', '.join(report.skipped_sections)}")

    typer.echo(f"Wrote knowledge base -> {settings.knowledge_base_md}")
    typer.echo(f"  {len(knowledge_base.personal_data)} personal data fields")
    typer.echo(f"  {len(knowledge_base.summaries)} summary variants")
    typer.echo(f"  {len(knowledge_base.experience)} experience bullets")
    typer.echo(f"  {len(knowledge_base.education)} education entries")
    typer.echo(f"  {len(knowledge_base.certifications)} certifications")
    typer.echo(f"  {len(knowledge_base.skills)} skills")
    typer.echo(f"  {len(knowledge_base.projects)} projects")
    typer.echo(f"  {len(knowledge_base.languages)} languages")
    typer.echo(f"  voice profile: {'yes' if knowledge_base.voice_profile else 'no'}")


@kb_app.command("audit")
def kb_audit() -> None:
    """Report personal-data fields with more than one distinct value
    across the CV corpus (phone, linkedin, github, ...).
    """
    container = Container(get_settings())
    if not container.knowledge_repository.exists():
        typer.echo("No knowledge base found. Run `cvpal kb build` first.", err=True)
        raise typer.Exit(1)

    knowledge_base = container.knowledge_repository.load()
    inconsistencies = audit_personal_data(knowledge_base)
    if not inconsistencies:
        typer.echo("No inconsistencies found.")
        return
    for item in inconsistencies:
        typer.echo(f"{item.field}:")
        for value in item.values:
            typer.echo(f"  - {value}")


@app.command()
def tailor(
    job_text: str = typer.Option(None, "--job-text", help="Job posting text, passed directly"),
    job_file: Path = typer.Option(
        None, "--job-file", help="Job posting file (.txt/.md/.docx)"
    ),
    job_url: str = typer.Option(
        None, "--job-url", help="Job posting URL (not yet supported by any agent - see AGENTS.md)"
    ),
    language: str = typer.Option(
        None, "--language", help="Force output language (e.g. 'en', 'es') instead of auto-detecting"
    ),
    output: Path = typer.Option(
        None, "--output", "-o", help="Where to write the tailored CV (default: data/outputs/)"
    ),
    document_format: str = typer.Option(
        "markdown", "--format", help="Output format: markdown, docx, or pdf"
    ),
) -> None:
    """Generate a CV tailored to a job posting, using ONLY the knowledge base."""
    settings = get_settings()
    container = Container(settings)

    if not container.knowledge_repository.exists():
        typer.echo("No knowledge base found. Run `cvpal kb build` first.", err=True)
        raise typer.Exit(1)

    provided = [v for v in (job_text, job_file, job_url) if v is not None]
    if len(provided) != 1:
        typer.echo("Provide exactly one of: --job-text, --job-file, --job-url", err=True)
        raise typer.Exit(1)

    try:
        fmt = DocumentFormat(document_format)
    except ValueError:
        valid = ", ".join(f.value for f in DocumentFormat)
        typer.echo(f"Unknown format '{document_format}'. Use one of: {valid}.", err=True)
        raise typer.Exit(1) from None

    agent = container.require(Capability.TEXT_COMPLETION)
    source = container.job_posting_source(text=job_text, file=job_file, url=job_url)
    knowledge_base_markdown = settings.knowledge_base_md.read_text()

    tailored = tailor_cv(
        source, knowledge_base_markdown, agent, container.detect_language, language_override=language
    )

    extension = {"markdown": "md", "docx": "docx", "pdf": "pdf"}[fmt.value]
    output_path = output or (settings.outputs_dir / f"cv-tailored-{tailored.language}.{extension}")

    try:
        result_path = container.document_renderer.render(
            tailored.content, document_format=fmt, output_path=output_path
        )
    except DocumentRenderError as exc:
        typer.echo(f"Render failed: {exc}", err=True)
        raise typer.Exit(1) from None

    typer.echo(f"Wrote tailored CV ({tailored.language}, {fmt.value}) -> {result_path}")


@agents_app.command("list")
def agents_list() -> None:
    """List registered agent providers."""
    settings = get_settings()
    for name in Container.available_agents():
        marker = " (active)" if name == settings.agent_name else ""
        typer.echo(f"{name}{marker}")


@agents_app.command("check")
def agents_check() -> None:
    """Round-trip a trivial prompt against the configured agent."""
    settings = get_settings()
    container = Container(settings)
    agent = container.agent

    typer.echo(f"Agent: {settings.agent_name}")
    typer.echo(f"Capabilities: {', '.join(c.value for c in agent.capabilities)}")
    result = agent.complete(CompletionRequest(prompt="Reply with exactly the word: ok"))
    typer.echo(f"Response: {result.text.strip()[:200]}")


@app.command("serve-mcp")
def serve_mcp() -> None:
    """Start the MCP server over stdio, for opencode/Claude Code/etc. to
    consume cv-pal as a tool, the same way they already consume engram.
    """
    from cvpal.interfaces.mcp.server import mcp

    mcp.run(transport="stdio")


if __name__ == "__main__":
    app()
