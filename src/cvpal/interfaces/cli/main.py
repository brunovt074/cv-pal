from __future__ import annotations

import logging
import os
import shutil
import sys
from pathlib import Path

import typer
from dotenv import load_dotenv

from cvpal.application.services.output_naming import build_output_filename
from cvpal.application.use_cases.audit_knowledge_base import audit_personal_data
from cvpal.application.use_cases.build_knowledge_base import build_knowledge_base
from cvpal.application.use_cases.clean_outputs import clean_outputs
from cvpal.application.use_cases.ingest_documents import ingest_documents
from cvpal.application.use_cases.tailor_cv import tailor_cv
from cvpal.config import REPO_ROOT, get_settings
from cvpal.container import Container
from cvpal.domain.capabilities import Capability
from cvpal.domain.errors import DocumentRenderError
from cvpal.domain.generation.models import DocumentFormat
from cvpal.domain.ports.text_completion import CompletionRequest
from cvpal.domain.user.profile import UserProfile
from cvpal.infrastructure.agents.registry import spec_for

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
    report = build_knowledge_base(
        documents, agent, settings.agent_name, container.checkpoint_store, settings.user.preferred_values
    )
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
        None, "--job-url", help="Job posting URL - fetched and stripped to readable text"
    ),
    company: str = typer.Option(
        "",
        "--company",
        help="Company name for the output filename (e.g. 'Proxify' -> '<your-slug>-cv-proxify.pdf'). "
        "Leave empty to use 'untitled'.",
    ),
    language: str = typer.Option(
        None, "--language", help="Output language (e.g. 'en', 'es'); defaults to English"
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
        source, knowledge_base_markdown, agent, language_override=language, company=company
    )

    extension = {"markdown": "md", "docx": "docx", "pdf": "pdf"}[fmt.value]
    default_name = build_output_filename(
        kind="cv", company=tailored.company, extension=extension, user_slug=settings.user.slug
    )
    output_path = output or (settings.outputs_dir / default_name)

    try:
        result_path = container.document_renderer.render(
            tailored.content, document_format=fmt, output_path=output_path
        )
    except DocumentRenderError as exc:
        typer.echo(f"Render failed: {exc}", err=True)
        raise typer.Exit(1) from None

    typer.echo(f"Wrote tailored CV ({tailored.language}, {fmt.value}) -> {result_path}")


@app.command()
def clean(
    filename: str = typer.Argument(
        None,
        help="Exact file name to delete from data/outputs/ (e.g. '<your-slug>-cv-proxify.pdf'). "
        "Omit when using --all.",
    ),
    all: bool = typer.Option(
        False, "--all", "-a", help="Delete every file in data/outputs/."
    ),
) -> None:
    """Delete tailored CV/cover-letter outputs.

    Pass an exact file name to remove a single document, or --all/-a to
    clear the entire outputs directory. Refuses to do anything if neither
    argument is supplied, to avoid accidental wipes.
    """
    settings = get_settings()
    settings.outputs_dir.mkdir(parents=True, exist_ok=True)
    result = clean_outputs(
        outputs_dir=settings.outputs_dir, filename=filename, remove_all=all
    )
    if not result.deleted:
        typer.echo(result.reason or "Nothing to delete.")
        raise typer.Exit(1)
    typer.echo(f"Deleted {len(result.deleted)} file(s):")
    for path in result.deleted:
        typer.echo(f"  - {path.name}")


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


def _migrate_legacy_data(data_dir: Path) -> None:
    """A checkout that pre-dates ~/.config/cvpal (or an env-var override
    pointing elsewhere) had its knowledge base at <repo>/data/ - offer to
    copy it into place rather than silently starting the user over.
    """
    legacy_dir = REPO_ROOT / "data"
    legacy_kb = legacy_dir / "knowledge-base.md"
    if not legacy_kb.exists() or (data_dir / "knowledge-base.md").exists():
        return
    if not typer.confirm(f"Found an existing knowledge base at {legacy_kb} - copy it here?", default=True):
        return
    data_dir.mkdir(parents=True, exist_ok=True)
    for name in ("knowledge-base.md", "cv-knowledge-base.xlsx", "ingested.json"):
        src = legacy_dir / name
        if src.exists():
            shutil.copy2(src, data_dir / name)
    legacy_checkpoints = legacy_dir / ".checkpoints"
    if legacy_checkpoints.is_dir():
        shutil.copytree(legacy_checkpoints, data_dir / ".checkpoints", dirs_exist_ok=True)
    typer.echo(f"Copied existing data into {data_dir}")


@app.command()
def init() -> None:
    """Interactive setup: writes ~/.config/cvpal/config.toml, creates the
    data directory, and offers to migrate a pre-existing knowledge base.
    Safe to re-run - shows current values as defaults.
    """
    settings = get_settings()
    default_profile = UserProfile()

    name = typer.prompt("Your name (used in the knowledge base header)", default=settings.user.name)
    default_slug = name.lower().replace(" ", "-")
    slug = typer.prompt(
        "Slug for output filenames (e.g. 'your-name-cv-acme.pdf')",
        default=settings.user.slug if settings.user.slug != default_profile.slug else default_slug,
    )
    phone = typer.prompt("Phone (optional)", default=settings.user.preferred_values.get("phone", ""))
    linkedin = typer.prompt(
        "LinkedIn URL (optional)", default=settings.user.preferred_values.get("linkedin", "")
    )
    github = typer.prompt("GitHub username (optional)", default=settings.user.preferred_values.get("github", ""))
    raw_dir = typer.prompt(
        "Directory containing your source CVs (PDF/DOCX/ODT)", default=str(settings.raw_dir)
    )
    provider = typer.prompt(
        f"Agent provider ({', '.join(Container.available_agents())})", default=settings.agent_name
    )

    raw_path = Path(raw_dir).expanduser()
    if not raw_path.exists() and typer.confirm(f"{raw_path} doesn't exist. Create it?", default=True):
        raw_path.mkdir(parents=True, exist_ok=True)

    config_text = f"""\
[user]
name = "{name}"
slug = "{slug}"

[user.preferred_values]
phone = "{phone}"
linkedin = "{linkedin}"
github = "{github}"

[paths]
raw_dir = "{raw_dir}"

[agent]
provider = "{provider}"
"""
    settings.config_file.parent.mkdir(parents=True, exist_ok=True)
    settings.config_file.write_text(config_text)
    typer.echo(f"\nWrote {settings.config_file}")

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    _migrate_legacy_data(settings.data_dir)

    kb_path = settings.data_dir / "knowledge-base.md"
    example = REPO_ROOT / "knowledge-base.example.md"
    if not kb_path.exists() and example.exists():
        if typer.confirm("No knowledge base found yet. Seed one from the example template?", default=False):
            shutil.copy2(example, kb_path)
            typer.echo(f"Wrote {kb_path} - edit it by hand or run 'cvpal ingest' + 'cvpal kb build'.")

    typer.echo(f"\nData directory: {settings.data_dir}")
    typer.echo("Run 'cvpal doctor' to verify everything is wired up.")


@app.command()
def doctor() -> None:
    """Diagnose whether cv-pal is ready to use: Python version, LibreOffice,
    config file, CV source directory, knowledge base, and the configured
    agent's binary.
    """
    all_ok = True

    def check(label: str, passed: bool, remedy: str = "") -> None:
        nonlocal all_ok
        typer.echo(f"{'✓' if passed else '✗'} {label}")
        if not passed:
            all_ok = False
            if remedy:
                typer.echo(f"  {remedy}")

    check(f"Python {sys.version.split()[0]} (>= 3.12 required)", sys.version_info >= (3, 12))
    check(
        "LibreOffice (soffice) installed",
        shutil.which("soffice") is not None,
        "Install LibreOffice for PDF rendering (docx/markdown formats still work without it).",
    )

    settings = get_settings()
    check(
        f"Config file: {settings.config_file}",
        settings.config_file.exists(),
        "Run 'cvpal init' to create it.",
    )

    raw_file_count = len(list(settings.raw_dir.glob("*"))) if settings.raw_dir.exists() else 0
    check(
        f"CV source directory: {settings.raw_dir} ({raw_file_count} files)",
        settings.raw_dir.exists() and raw_file_count > 0,
        "Point it at a folder with your CVs (PDF/DOCX/ODT) - run 'cvpal init' or set CV_RAW_DIR.",
    )

    check(
        f"Knowledge base: {settings.knowledge_base_md}",
        settings.knowledge_base_md.exists(),
        "Run 'cvpal ingest' then 'cvpal kb build'.",
    )

    spec = spec_for(settings.agent_name)
    if spec is None:
        check(f"Agent '{settings.agent_name}' recognized", False, "Run 'cvpal agents list' for valid providers.")
    else:
        binary = os.environ.get(spec.binary_env_var, spec.default_binary)
        check(
            f"Agent '{settings.agent_name}' binary ('{binary}') in PATH",
            shutil.which(binary) is not None,
            f"Install {binary}, or set CVPAL_AGENT to a different provider ('cvpal agents list').",
        )

    try:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        writable = os.access(settings.data_dir, os.W_OK)
    except OSError:
        writable = False
    check(f"Data directory writable: {settings.data_dir}", writable)

    typer.echo()
    if not all_ok:
        typer.echo("Some checks failed - see remedies above.")
        raise typer.Exit(1)
    typer.echo("All checks passed - ready to go.")


@app.command("serve-mcp")
def serve_mcp() -> None:
    """Start the MCP server over stdio, for opencode/Claude Code/etc. to
    consume cv-pal as a tool, the same way they already consume engram.
    """
    from cvpal.interfaces.mcp.server import mcp

    mcp.run(transport="stdio")


if __name__ == "__main__":
    app()
