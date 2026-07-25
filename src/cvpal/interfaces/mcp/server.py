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

from mcp.server.fastmcp import FastMCP

from cvpal.application.prompts.cv_pal import cv_pal_prompt
from cvpal.application.services.agent_view import render_agent_view
from cvpal.application.services.markdown_sections import extract_section_block
from cvpal.application.use_cases.audit_knowledge_base import audit_personal_data
from cvpal.application.use_cases.build_knowledge_base import build_knowledge_base
from cvpal.application.use_cases.ingest_documents import ingest_documents
from cvpal.application.use_cases.update_knowledge_base import (
    update_knowledge_base as apply_knowledge_base_update,
)
from cvpal.config import get_settings
from cvpal.container import Container
from cvpal.domain.capabilities import Capability
from cvpal.domain.errors import CapabilityNotSupportedError, DocumentRenderError
from cvpal.domain.generation.models import DocumentFormat

mcp = FastMCP("cvpal")

_NO_KB_MESSAGE = (
    "No knowledge base found yet. Ask the user to run `cvpal ingest` then `cvpal kb build`, "
    "or call the rebuild_knowledge_base tool (it will ingest first if needed)."
)


def _container() -> Container:
    return Container(get_settings())


def _cv_pal(
    container: Container,
    job_posting_text: str,
    job_posting_file: str,
    language: str,
) -> str:
    if not container.knowledge_repository.exists():
        return _NO_KB_MESSAGE
    if bool(job_posting_text) == bool(job_posting_file):
        return "Provide exactly one of job_posting_text or job_posting_file."

    source = container.job_posting_source(
        text=job_posting_text or None,
        file=Path(job_posting_file) if job_posting_file else None,
    )
    posting = source.read()
    detected = container.detect_language(posting.raw_text)
    resolved_language = language or (detected if detected != "unknown" else "en")

    kb = container.knowledge_repository.load()
    agent_view = render_agent_view(kb)
    return cv_pal_prompt(agent_view, posting.raw_text, resolved_language, kb.voice_profile)


@mcp.prompt()
def cv_pal(job_posting_text: str = "", job_posting_file: str = "", language: str = "") -> str:
    """Tailor a CV (and, on request, a cover letter) to a job posting using
    the user's knowledge base. Provide exactly one of job_posting_text
    (pasted text) or job_posting_file (path to a .txt/.md/.docx file).
    Leave language empty to infer it from the posting.
    """
    return _cv_pal(_container(), job_posting_text, job_posting_file, language)


def _get_cv_material(container: Container) -> str:
    if not container.knowledge_repository.exists():
        return _NO_KB_MESSAGE
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
        return _NO_KB_MESSAGE
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
        return _NO_KB_MESSAGE
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
        return _NO_KB_MESSAGE
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
    report = build_knowledge_base(documents, agent, container.settings.agent_name, container.checkpoint_store)
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


def _render_document(container: Container, markdown: str, document_format: str, filename: str) -> str:
    try:
        fmt = DocumentFormat(document_format)
    except ValueError:
        valid = ", ".join(f.value for f in DocumentFormat)
        return f"Unknown format '{document_format}'. Use one of: {valid}."

    output_path = container.settings.outputs_dir / filename
    try:
        result_path = container.document_renderer.render(
            markdown, document_format=fmt, output_path=output_path
        )
    except DocumentRenderError as exc:
        return f"Render failed: {exc}"
    return f"Wrote {fmt.value} -> {result_path}"


@mcp.tool()
def render_document(markdown: str, document_format: str, filename: str) -> str:
    """Convert markdown (a CV or cover letter you just wrote) into a real
    file under data/outputs/. document_format is one of: markdown, docx,
    pdf. filename is just the file name, e.g. "cv-acme-backend.pdf" - no
    agent or API key needed, this runs locally.
    """
    return _render_document(_container(), markdown, document_format, filename)
