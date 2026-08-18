"""cv-pal as an MCP server - the tool surface any MCP-capable agent
(opencode, Claude Code, ...) consumes over stdio, the same way it already
consumes engram. The host agent writes the CV/cover letter; cv-pal
provides material, the assembled `/cv-pal` prompt, and deterministic
actions. See skills/mcp-server/SKILL.md for the full contract and
AGENTS.md's Architecture section for why this is just another interface
adapter next to interfaces/cli/.

Every handler is a thin wrapper: build a Container, delegate to an
application use case or service, format the result as text. The
underlying `_verb(...)` functions take the Container explicitly so tests
can call them directly without touching the MCP protocol or real
environment - the `@mcp.tool()`/`@mcp.prompt()` functions themselves have
no extra parameters, since anything beyond the documented arguments would
leak into the schema an agent sees.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from cvpal.application.prompts.cv_pal import cv_pal_prompt
from cvpal.application.services.agent_view import render_agent_view
from cvpal.application.services.markdown_sections import extract_section_block
from cvpal.application.services.output_naming import build_output_path
from cvpal.application.use_cases.audit_knowledge_base import audit_personal_data
from cvpal.application.use_cases.build_knowledge_base import build_knowledge_base
from cvpal.application.use_cases.configure_user import write_user_config
from cvpal.application.use_cases.ingest_documents import ingest_documents
from cvpal.application.use_cases.update_knowledge_base import (
    update_knowledge_base as apply_knowledge_base_update,
)
from cvpal.config import get_settings
from cvpal.container import Container
from cvpal.domain.capabilities import Capability
from cvpal.domain.errors import CapabilityNotSupportedError, DocumentRenderError, JobPostingFetchError
from cvpal.domain.generation.models import DocumentFormat

mcp = FastMCP("cvpal")


def _container() -> Container:
    return Container(get_settings())


def _onboarding_message(container: Container) -> str:
    """What to tell the host agent instead of a bare "no knowledge base" -
    distinguishes never-configured from configured-but-no-source-files from
    configured-with-files-but-not-ingested-yet, so the guidance is always
    actionable rather than a dead end.
    """
    settings = container.settings
    if not settings.config_file.exists():
        return (
            "First-time setup - no configuration found yet. Ask the user (1) which folder "
            "contains their CV/resume files (PDF/DOCX/ODT), and (2) what language they'd like "
            "CVs drafted in by default (e.g. 'en', 'es'). Then call the configure tool with "
            "their answers, followed by ingest_corpus and rebuild_knowledge_base."
        )
    has_source_files = settings.raw_dir.exists() and bool(
        container.document_parser.discover(settings.raw_dir)
    )
    if not has_source_files:
        return (
            f"No CV source files found at {settings.raw_dir}. Ask the user where their CV/resume "
            "files are, call the configure tool with raw_dir set to that path, then call "
            "ingest_corpus and rebuild_knowledge_base."
        )
    return (
        "No knowledge base found yet. Call ingest_corpus then rebuild_knowledge_base "
        "(or just rebuild_knowledge_base - it ingests first if needed)."
    )


def _cv_pal(
    container: Container,
    job_posting_text: str,
    job_posting_file: str,
    job_posting_url: str,
    language: str,
) -> str:
    if not container.knowledge_repository.exists():
        return _onboarding_message(container)
    provided = [v for v in (job_posting_text, job_posting_file, job_posting_url) if v]
    if len(provided) != 1:
        return "Provide exactly one of job_posting_text, job_posting_file, or job_posting_url."

    source = container.job_posting_source(
        text=job_posting_text or None,
        file=Path(job_posting_file) if job_posting_file else None,
        url=job_posting_url or None,
    )
    try:
        posting = source.read()
    except JobPostingFetchError as exc:
        return str(exc)
    resolved_language = language or container.settings.user.default_language

    kb = container.knowledge_repository.load()
    agent_view = render_agent_view(kb)
    return cv_pal_prompt(agent_view, posting.raw_text, resolved_language, kb.voice_profile)


@mcp.prompt()
def cv_pal(
    job_posting_text: str = "",
    job_posting_file: str = "",
    job_posting_url: str = "",
    language: str = "",
) -> str:
    """Tailor a CV (and, on request, a cover letter) to a job posting using
    the user's knowledge base. Provide exactly one of job_posting_text
    (pasted text), job_posting_file (path to a .txt/.md/.docx file), or
    job_posting_url (a link to the posting - fetched and stripped to
    readable text). Leave language empty to use the user's configured
    default language (English unless changed via the configure tool).
    """
    return _cv_pal(_container(), job_posting_text, job_posting_file, job_posting_url, language)


def _get_cv_material(container: Container) -> str:
    if not container.knowledge_repository.exists():
        return _onboarding_message(container)
    return render_agent_view(container.knowledge_repository.load())


@mcp.tool()
def get_cv_material() -> str:
    """Lean, agent-optimized markdown view of the knowledge base - no
    provenance, no superseded personal-data variants. Use this instead of
    get_knowledge_base when drafting a CV/cover letter yourself.
    """
    return _get_cv_material(_container())


def _get_knowledge_base(container: Container, section: str) -> str:
    if not container.knowledge_repository.exists():
        return _onboarding_message(container)
    full_text = container.settings.knowledge_base_md.read_text()
    if not section:
        return full_text
    block = extract_section_block(full_text, section)
    if block is None:
        return f"No section '{section}' found. Ask for the full document instead."
    return block.strip()


@mcp.tool()
def get_knowledge_base(section: str = "") -> str:
    """Full knowledge base markdown, with provenance (source files per
    fact) - the human-editable view. Leave section empty for the whole
    document, or pass a section key (personal_data, summaries, experience,
    education, certifications, skills, projects, languages, voice_profile).
    """
    return _get_knowledge_base(_container(), section)


def _update_knowledge_base(container: Container, markdown: str, force: bool) -> str:
    if not container.knowledge_repository.exists():
        return _onboarding_message(container)
    current = container.knowledge_repository.load()
    result = apply_knowledge_base_update(
        current, markdown, container.parse_knowledge_base_markdown, force=force
    )
    if not result.accepted:
        return f"Update rejected: {result.reason}"

    backup_path = container.knowledge_repository.backup()
    container.settings.knowledge_base_md.write_text(markdown)
    return f"Knowledge base updated. Previous version backed up to {backup_path}."


@mcp.tool()
def update_knowledge_base(markdown: str, force: bool = False) -> str:
    """Overwrite the knowledge base with edited markdown (e.g. after
    adding a project, tweaking a bullet, or saving a newly-elicited voice
    profile). Backs up the previous version first. Rejects an apparent
    near-total wipe unless force=True.
    """
    return _update_knowledge_base(_container(), markdown, force)


def _audit_knowledge_base(container: Container) -> str:
    if not container.knowledge_repository.exists():
        return _onboarding_message(container)
    inconsistencies = audit_personal_data(container.knowledge_repository.load())
    if not inconsistencies:
        return "No inconsistencies found."
    lines: list[str] = []
    for item in inconsistencies:
        lines.append(f"{item.field}:")
        lines.extend(f"  - {value}" for value in item.values)
    return "\n".join(lines)


@mcp.tool()
def audit_knowledge_base() -> str:
    """Report personal-data fields with more than one distinct value
    across the CV corpus (phone, linkedin, github, ...)."""
    return _audit_knowledge_base(_container())


def _configure(
    container: Container, raw_dir: str, default_language: str, name: str, slug: str
) -> str:
    write_user_config(
        container.settings.config_file,
        name=name or None,
        slug=slug or None,
        default_language=default_language or None,
        raw_dir=raw_dir or None,
    )
    return (
        f"Saved to {container.settings.config_file}. Next: call ingest_corpus, then "
        "rebuild_knowledge_base."
    )


@mcp.tool()
def configure(
    raw_dir: str = "",
    default_language: str = "",
    name: str = "",
    slug: str = "",
) -> str:
    """Set up cv-pal for a new user, conversationally - call this whenever
    another tool reports no configuration found yet. Ask the user for
    whichever fields you don't already have:
    - raw_dir: folder containing their CV/resume files (PDF/DOCX/ODT)
    - default_language: e.g. 'en', 'es' - CVs are drafted in this language
      unless a specific request overrides it
    - name, slug: used in the knowledge base header and output file names
      (e.g. slug "jane-doe" -> "jane-doe-cv-acme.pdf"); safe to leave these
      two for later, raw_dir and default_language matter most up front
    Only pass what you have - anything left blank keeps its existing
    value, so this is safe to call more than once as you gather answers.
    """
    return _configure(_container(), raw_dir, default_language, name, slug)


def _ingest_corpus(container: Container) -> str:
    previous = (
        container.raw_document_repository.load()
        if container.raw_document_repository.exists()
        else None
    )
    result = ingest_documents(container.settings.raw_dir, container.document_parser, previous=previous)
    container.raw_document_repository.save(result.documents)
    return (
        f"Ingested {len(result.documents)} documents from {container.settings.raw_dir}: "
        f"{result.reused_count} unchanged (skipped), {result.reparsed_count} parsed."
    )


@mcp.tool()
def ingest_corpus() -> str:
    """Re-scan the CV source directory, parsing only files that changed
    since the last ingest. Run this after adding/editing CVs, before
    rebuild_knowledge_base."""
    return _ingest_corpus(_container())


def _rebuild_knowledge_base(container: Container) -> str:
    if not container.raw_document_repository.exists():
        return "No ingested documents found. Call ingest_corpus first."
    try:
        agent = container.require(Capability.TEXT_COMPLETION, Capability.JSON_COMPLETION)
    except CapabilityNotSupportedError as exc:
        return f"Configured agent can't do this: {exc}"

    documents = container.raw_document_repository.load()
    report = build_knowledge_base(
        documents,
        agent,
        container.settings.agent_name,
        container.checkpoint_store,
        container.settings.user.preferred_values,
    )
    container.knowledge_repository.save(report.knowledge_base)

    if not report.rebuilt_sections:
        return "Knowledge base already up to date - no section changed, zero agent calls made."
    skipped = ", ".join(report.skipped_sections) or "(none)"
    return f"Rebuilt: {', '.join(report.rebuilt_sections)}. Unchanged: {skipped}."


@mcp.tool()
def rebuild_knowledge_base() -> str:
    """Regenerate the knowledge base from ingested CVs via the configured
    agent. Safe to call defensively - a section whose underlying CVs
    haven't changed since the last run costs zero agent calls; only
    actually-changed sections are recomputed."""
    return _rebuild_knowledge_base(_container())


def _render_document(
    container: Container,
    markdown: str,
    document_format: str,
    filename: str,
    kind: str = "",
    company: str = "",
) -> str:
    try:
        fmt = DocumentFormat(document_format)
    except ValueError:
        valid = ", ".join(f.value for f in DocumentFormat)
        return f"Unknown format '{document_format}'. Use one of: {valid}."

    extension = {"markdown": "md", "docx": "docx", "pdf": "pdf"}[fmt.value]
    if kind:
        try:
            output_name = build_output_path(
                kind=kind, company=company, extension=extension, user_slug=container.settings.user.slug
            )
        except ValueError as exc:
            return f"Unknown kind '{kind}'. {exc}"
    else:
        output_name = filename

    output_path = container.settings.outputs_dir / output_name
    try:
        result_path = container.document_renderer.render(
            markdown, document_format=fmt, output_path=output_path
        )
    except DocumentRenderError as exc:
        return f"Render failed: {exc}"
    return f"Wrote {fmt.value} -> {result_path}"


@mcp.tool()
def render_document(
    markdown: str,
    document_format: str,
    filename: str = "",
    kind: str = "",
    company: str = "",
) -> str:
    """Convert markdown (a CV or cover letter you just wrote) into a real
    file under data/outputs/. document_format is one of: markdown, docx,
    pdf.

    Two ways to name the file:
    - Pass kind="cv" (or "cover_letter") and company="<name>" and the
      tool will build the conventional file name for you
      (<your-slug>-cv-<company-slug>.{ext} for CVs,
      <your-slug>-cl-<company-slug>.{ext} for cover letters). This is the
      recommended path - it keeps every output named the same way.
    - Or pass an explicit filename. Used only when you need to override
      the convention (e.g. debug dumps).

    No agent or API key needed - this runs locally.
    """
    return _render_document(_container(), markdown, document_format, filename, kind, company)


def main() -> None:
    """Entry point for the `cvpal-mcp` console script (and `cvpal serve-mcp`,
    which just imports and calls this). Loads .env itself, unlike the CLI's
    `mcp = FastMCP(...)` module import alone - a host launching this module
    directly (`uvx cv-pal cvpal-mcp`) never goes through interfaces/cli/main.py,
    which is otherwise the only place .env gets loaded.
    """
    load_dotenv()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
