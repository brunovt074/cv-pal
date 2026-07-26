# CV-Pal — Agent Guidelines

> Single Source of Truth for all AI coding agents working on this project.
> Compatible with: Claude Code, Codex, Cursor, Windsurf, Gemini CLI, Copilot, Aider, Junie.

---

## Agent Startup Protocol

Before writing any code, every agent MUST:

1. Read this file completely
2. Read `PROJECT_STATUS.md` to understand current state and branch chain
3. If a persistent-memory tool (e.g. engram) is available in this environment, query it for prior
   decisions on this project - skip this step if none is configured
4. Identify which skill(s) apply to the task (see Auto-invoke table below)
5. Read the relevant `skills/{name}/SKILL.md` file(s)
6. Confirm the target branch before any file modification

Skipping this protocol produces inconsistent code and failed reviews.

---

## Project Overview

| Field | Value |
|-------|-------|
| Name | CV-Pal |
| Language | Python 3.12 |
| Purpose | A programmatic, agent-agnostic tool for CV/cover-letter tailoring — consumed by AI agents (opencode, Claude Code) over MCP, not just a standalone pipeline. Consolidates scattered CV/cover-letter documents (any number, multiple stacks/languages) into a knowledge base, then any host agent tailors a CV/cover letter to a job posting using it |
| Architecture | Hexagonal (ports & adapters) — see below. Pipeline (ingest → build knowledge base) + two interface adapters: CLI (`cvpal ...`) and MCP server (`cvpal serve-mcp`) |
| Knowledge base | `data/knowledge-base.md` — source of truth, editable by a human or any agent |
| Primary consumption path | MCP over stdio (`cvpal serve-mcp`) — an agent calls the `cv_pal` prompt with a job posting, gets an assembled one-shot prompt (lean knowledge base + protocol), and drafts + prints the CV/cover letter itself. See "MCP server" below |
| AI engine | Provider-agnostic by design — see Architecture. Default today: `opencode` CLI, model `opencode-go/deepseek-v4-pro`. A second CLI adapter (Claude Code) already exists to prove the abstraction holds. Only used for `rebuild_knowledge_base` (batch extraction) - the primary MCP flow has no LLM call inside cv-pal at all, the host agent does the writing |
| API + CLI | FastAPI (not planned anymore, superseded by MCP) + Typer CLI (`src/cvpal/interfaces/cli/`) + MCP server (`src/cvpal/interfaces/mcp/`) |

### Architecture

Hexagonal / ports & adapters. Dependency direction: `interfaces → application → domain`.
`infrastructure` implements `domain` ports; **only `container.py`** (the composition root) is
allowed to import both `domain` and `infrastructure` and wire them together — use cases and
`interfaces/` never import an infrastructure adapter directly, they ask the container. Verify this
holds with `grep -rln "cvpal.infrastructure" src/cvpal/application src/cvpal/domain` (must be
empty) before merging any change that touches these layers.

| Layer | Location | Contains |
|-------|----------|----------|
| Domain | `src/cvpal/domain/` | Pydantic models (`documents/`, `knowledge/`, `jobs/`, `generation/`), ports as `typing.Protocol` (`ports/`), `Capability` enum, error hierarchy. Zero infrastructure imports |
| Application | `src/cvpal/application/` | Use cases (`use_cases/`), prompt templates (`prompts/`), pure services (`services/` — dedupe, checkpointing helpers, response parsing, personal-data correction, `agent_view.py` lean projection, `markdown_sections.py`). Depends only on `domain` |
| Infrastructure | `src/cvpal/infrastructure/` | Port implementations: `agents/` (CLI-driven text-completion adapters), `parsers/` (PDF/DOCX/ODT extraction), `persistence/` (markdown/JSON repositories, checkpoint store), `job_postings/` (text/file/URL sources), `rendering/` (local `.docx`/`.pdf` renderer, no agent needed) |
| Interfaces | `src/cvpal/interfaces/cli/`, `src/cvpal/interfaces/mcp/` | Two adapters over the same use cases: Typer CLI and an MCP server (stdio). Both resolve everything through `container.py`, never import `infrastructure` directly |

### MCP server (primary interface)

`cvpal serve-mcp` starts an MCP server over stdio - the same way this project already consumes
engram from opencode. It's implemented in `src/cvpal/interfaces/mcp/server.py` with the official
`mcp` SDK's `FastMCP`. Every handler is a thin wrapper: build a `Container`, call an application
use case/service, format the result as text - the actual logic lives in `application/`, testable
without touching the MCP protocol (see `tests/interfaces/test_mcp_server.py`, which calls the
private `_verb(container, ...)` functions directly).

**The host agent writes, cv-pal provides.** The `cv_pal` MCP prompt is the primary entry point: it
assembles a lean knowledge base view + the job posting + a conversational protocol into one prompt,
and returns it to the host - the host's own model drafts and PRINTS the CV (and, on request, a
cover letter) in its own conversation. cv-pal never calls an LLM to do this; the only tool that
calls an agent internally is `rebuild_knowledge_base` (the batch extraction pipeline), and it's
safe to call defensively since it's a no-op when the CV corpus hasn't changed (see the
content-addressed checkpointing entry in the Decision Log).

Tool/prompt surface: `cv_pal` (prompt), `get_cv_material`, `get_knowledge_base`,
`update_knowledge_base`, `audit_knowledge_base`, `ingest_corpus`, `rebuild_knowledge_base`,
`render_document` (tools). See `skills/mcp-server/SKILL.md` for the full contract and design
rationale per tool.

**Agent-agnosticism mechanism** (`infrastructure/agents/`): every CLI-driven provider (opencode,
Claude Code, Codex, Gemini CLI, ...) follows the same shape — launch a binary with a prompt, parse
its stdout. That shape is declared once as `CliAgentSpec` (`infrastructure/agents/spec.py`) and
executed by one generic `CliAgentAdapter`. Adding a new provider is one spec + one parser function
in `infrastructure/agents/cli/`, plus one line in `infrastructure/agents/registry.py` — zero
changes to any use case. Select the active provider via `CVPAL_AGENT` (env var, default
`opencode`); override per-provider binary/model via `<PROVIDER>_BIN` / `<PROVIDER>_MODEL`.

**Capabilities, not a single monolithic port**: `domain/capabilities.py:Capability` enum
(`TEXT_COMPLETION`, `JSON_COMPLETION`, `DOCUMENT_RENDER`, `WEB_CONTENT`, `FILE_ATTACH`).
`container.require(*capabilities)` raises `CapabilityNotSupportedError` immediately if the
configured agent can't do everything a use case needs — fail at wiring time, not mid-pipeline.
Only `TEXT_COMPLETION`/`JSON_COMPLETION` are agent capabilities today (used by
`rebuild_knowledge_base`). `DOCUMENT_RENDER` turned out not to need an agent at all -
`infrastructure/rendering/local_document_renderer.py` does it locally with `python-docx` +
`soffice` (see Decision Log) - so `DocumentRenderPort` is wired directly via
`container.document_renderer`, bypassing the capability-negotiation dance entirely. `WEB_CONTENT`
(fetching a job posting URL) still has no adapter - do not assume opencode categorically can't do
it either, it has a native `webfetch` tool and MCP support; the actual blocker is non-interactive
`run` mode auto-denying tool permissions.

### Component Layout

| Component | Location | Purpose |
|-----------|----------|---------|
| Domain models & ports | `src/cvpal/domain/` | Data shapes + boundary contracts, no I/O |
| Ingestion | `src/cvpal/infrastructure/parsers/`, `application/use_cases/ingest_documents.py` | Extract structured data from PDF/DOCX/ODT source documents, skipping files unchanged since the last run |
| Knowledge base build | `application/use_cases/build_knowledge_base.py`, `application/prompts/`, `infrastructure/persistence/markdown_knowledge_repository.py` | Dedupe, extract via agent (content-addressed checkpointing per section), validate, render `data/knowledge-base.md` |
| Lean agent view | `application/services/agent_view.py` | Strips provenance + superseded personal-data variants for token-efficient agent consumption |
| Tailoring | `application/use_cases/tailor_cv.py`, `application/prompts/cv_pal.py`, `infrastructure/job_postings/` | Generate a CV (CLI path) or assemble the one-shot `/cv-pal` prompt (MCP path) for a job posting |
| Document rendering | `infrastructure/rendering/local_document_renderer.py` | Markdown → real `.docx`/`.pdf`, no agent or API key needed |
| Agent layer | `src/cvpal/infrastructure/agents/`, `src/cvpal/container.py` | Provider-agnostic text-completion adapters + composition root |
| CLI | `src/cvpal/interfaces/cli/main.py` | Typer entry point (`cvpal` console script) |
| MCP server | `src/cvpal/interfaces/mcp/server.py` | Primary interface - see "MCP server" above |
| Skills | `skills/` | Agent behavior, coding patterns, quality gates |

---

## Setup & Validation Commands

```bash
# Install (editable, with dev deps)
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src tests

# Full pre-merge validation
ruff check src tests && pytest
```

## CLI Commands

```bash
cvpal init                                        # Interactive setup wizard (config.toml, data dir, migration)
cvpal doctor                                      # Environment diagnostics
cvpal ingest                                       # Parse changed source docs (CV_RAW_DIR) into data/ingested.json
cvpal kb build                                    # Build/refresh data/knowledge-base.md (only changed sections)
cvpal kb audit                                    # Report personal-data fields with multiple distinct values
cvpal tailor --job-text "..." --format pdf        # Generate a tailored CV (markdown/docx/pdf)
cvpal tailor --job-file posting.docx --format docx # ...from a local .txt/.md/.docx file
cvpal clean --all                                 # Delete generated outputs
cvpal agents list                                 # List registered agent providers
cvpal agents check                                # Round-trip a trivial prompt against the configured agent
cvpal serve-mcp                                   # Start the MCP server over stdio (primary interface)
```

Not yet implemented: `cvpal sync` (Google Sheets), `cvpal profile <platform>` (freelance
profiles), HTTP/SSE MCP transport (deliberately out of scope - see Decision Log).

---

## Code Style

- No comments in production code — naming and structure must explain intent
- Code identifiers (functions, classes, variables, files, packages) in English
- **Knowledge base content is English by default** — see Decision Log. Translation to another
  language happens only at tailoring time, never stored as a duplicate
- Type hints on all public functions; pydantic models for all structured data crossing a
  module boundary
- Ports are `typing.Protocol` in `domain/ports/`; adapters implement them structurally (no base
  class inheritance required)
- No garbage tests (`assert True`, no-op assertions)

---

## Git & Branch Strategy

- NEVER commit directly to `master`
- Use feature branches with descriptive names: `feature/descriptive-name`
- Atomic conventional commits: `feat:`, `fix:`, `test:`, `refactor:`, `chore:`
- Branch chaining is allowed and preferred over direct merge to `master`

Current chain:

```
master
  <- feature/initial-config
      <- feature/data-pipeline        (ingest + legacy .xlsx analytics)
          <- feature/hexagonal-agents (ports & adapters, agent-agnostic core, markdown KB, tailoring)
              <- feature/mcp-server    (MCP server as primary interface, local document renderer,
                                        content-addressed incremental checkpointing, lean agent view)
                  <- feature/freelance-profiles
                      <- feature/web-job-search   (future iteration; can reuse the WebContentPort
                                                    adapter added in feature/mcp-server)
```

`feature/generation-engine` (previously planned to add a `DocumentRenderPort` adapter) was folded
into `feature/mcp-server` - turned out to need no agent at all, just `python-docx` + `soffice`.

`feature/voice-profile` (previously planned as its own branch) was folded into
`feature/hexagonal-agents` — voice extraction is now one section of `build_knowledge_base()`,
not a separate pipeline stage.

---

## Skills

### Available Skills

| Skill | File | Scope |
|-------|------|-------|
| `data-extraction` | `skills/data-extraction/SKILL.md` | `infrastructure/parsers/`, `application/use_cases/ingest_documents.py` |
| `data-analytics` | `skills/data-analytics/SKILL.md` | `application/use_cases/build_knowledge_base.py`, `application/prompts/extraction.py`, `application/services/`, `infrastructure/persistence/markdown_knowledge_repository.py` |
| `voice-style` | `skills/voice-style/SKILL.md` | `domain/knowledge/voice.py`, `application/prompts/voice.py` |
| `cv-generation` | `skills/cv-generation/SKILL.md` | `application/use_cases/tailor_cv.py`, `application/prompts/tailoring.py`, `application/prompts/cv_pal.py`, `infrastructure/job_postings/`, `infrastructure/rendering/` |
| `mcp-server` | `skills/mcp-server/SKILL.md` | `interfaces/mcp/server.py`, `application/services/agent_view.py` — the tool/prompt contract and design rationale per handler |
| `freelance-profiles` | `skills/freelance-profiles/SKILL.md` | (not yet implemented — see Not Started in PROJECT_STATUS.md) |
| `qa-code` | `skills/qa-code/SKILL.md` | shared |
| `skill-creator` | `skills/skill-creator/SKILL.md` | skills/ |

### Auto-invoke Rules

| Action | Read This Skill |
|--------|------------------|
| Adding/modifying a document parser (PDF/DOCX/ODT) | `data-extraction` |
| Changing dedupe/extraction-prompt/knowledge-base-schema logic | `data-analytics` |
| Changing the markdown knowledge base's table shape | `data-analytics` |
| Extracting or applying the voice/style profile | `voice-style` |
| Building CV/cover-letter tailoring prompts | `cv-generation` |
| Adding a `WebContentPort` adapter, or changing document rendering | `cv-generation` |
| Adding/changing an MCP tool or the `cv_pal` prompt | `mcp-server` |
| Adding a new agent provider (CLI or SDK) | read `infrastructure/agents/spec.py` + `registry.py` docstrings directly |
| Generating a freelance platform profile | `freelance-profiles` |
| Running code quality audits or refactors | `qa-code` |
| Creating a new skill | `skill-creator` |

---

## Decision Log

Architectural decisions made — do not relitigate without strong evidence:

| Decision | Rationale |
|----------|-----------|
| Full app (not just Sheets + Claude web) | Historias 3-4 need real code: platform integrations and web search can't run from Claude web alone |
| Hexagonal architecture (`domain`/`application`/`infrastructure`/`interfaces`) | The system must be agent-agnostic today (opencode for testing) and provider-agnostic tomorrow (Claude Code, Anthropic SDK, or anything else) without touching use cases. Confirmed explicitly; the LLM backend was already a single hardcoded call site (`llm/opencode_client.py`) that every analytics module imported directly, which would have meant touching every call site to add a second provider |
| `data/knowledge-base.md` replaces `.xlsx` as the source of truth | Decided in an earlier analysis pass: any agent reads markdown natively without a parsing step; a human can hand-edit it directly and diff it in git. An optional `.xlsx` export existed for a while as a secondary output for spreadsheet review, but was never wired into any CLI/MCP command - removed outright rather than kept as unreachable code (`infrastructure/persistence/xlsx_exporter.py` and `cv_version_inventory.py`, both deleted) |
| Extraction prompts return JSON validated against domain models, never markdown text directly | A deterministic renderer (`markdown_knowledge_repository.save()`) turns the validated `KnowledgeBase` into markdown afterward. This makes `build_knowledge_base()` testable with a scripted `FakeTextAgent` and no live LLM call, and guarantees the file's shape regardless of how faithfully an agent follows formatting instructions |
| Markdown knowledge base uses per-field tables + a free-form `Notes` section, not bespoke prose formatting per section type | One generic table renderer/parser works for every record-based section (`PersonalDataField`, `ExperienceBullet`, `SkillEntry`, ...) — far less code than a bespoke parser per section, and just as human-editable. `Notes` is preserved verbatim across `cvpal kb build` reruns for anything that doesn't fit a table row |
| Which personal-data value is "current" (phone, LinkedIn, GitHub) is a hardcoded fact, never an LLM guess | `application/services/personal_data_resolution.py` applies known-authoritative values as a deterministic post-processing pass. An agent extracts all distinct values found across the corpus; only a human can say which one is real. Caught a real substring-matching bug here during implementation ("-dev" matching inside "-developer") — covered by `tests/application/test_personal_data_resolution.py` against the actual corpus's known-inconsistent values |
| Knowledge base content in English by default | Avoids maintaining ES/EN duplicates; translation happens on-the-fly per job application at tailoring time |
| Tailored CV/cover-letter output defaults to English, never inferred from the job posting's language | Explicit user decision, superseding the earlier posting-language-detection default. `tailor_cv()` (CLI path) and `_cv_pal()` (MCP path) now resolve `language_override or "en"` — no `detect_language` call in either. Only an explicit `--language`/`language` argument changes the output language; `infrastructure/parsers/sections.py:detect_language` is still used for ingestion (tagging source documents' language), unrelated to this |
| Voice/tone extracted from existing cover letters, as one section of the same knowledge-base build pass | The letters are the ground truth for sounding like the author — no separate interview or pipeline stage needed |
| Freelance profiles = human-in-the-loop | Upwork/Fiverr ToS prohibit account automation; agent generates content, human pastes/reviews. API automation only where a real API exists (e.g. Himalayas/boards) |
| Text-generation tasks go through a `TextCompletionPort`, default adapter `opencode` CLI (`opencode-go/deepseek-v4-pro`) | Explicit user decision. `infrastructure/agents/cli/opencode.py` shells out to the already-authenticated `opencode` CLI instead of reading its credential store directly. A second adapter (`cli/claude_code.py`, Claude Code CLI) exists specifically to prove the `CliAgentSpec` abstraction generalizes beyond opencode, not just in theory |
| Per-section agent calls, not one giant call | A single call covering all CV sections at once triggers unreliable behavior in non-interactive CLI agent modes: tool-call permissions are auto-denied, so a large response the model tries to write to a scratch file silently produces empty output. Splitting into one small call per canonical section (personal_data, summary, experience, education+certifications, skills, projects, languages, voice_profile) keeps outputs small enough to return reliably |
| `source_files` capped at 3 representative files per record | Uncapped lists blew up JSON output size for near-universal facts (e.g. a skill appearing in most of a large CV corpus), truncating the response mid-string. Traceability doesn't need every duplicate, just a representative sample |
| Checkpoint every agent-backed structuring step to disk | Individual pipeline runs can exceed a harness's background-execution time limit; checkpointing each step's result (`data/.checkpoints/`, gitignored, via `CheckpointStorePort`) lets `cvpal kb build` be re-run in short bursts, resuming instead of re-paying completed calls |
| Checkpoints are content-addressed (fingerprint of the section's input + a `PROMPT_VERSION` constant), not existence-based | The prior scheme reused a checkpoint just because the file existed, regardless of whether the source CVs had changed - stale on any edit, and forced a full `rm -rf .checkpoints` to recompute even a single changed section. Now a section is only recomputed when its own deduped input actually changed, which makes `rebuild_knowledge_base` genuinely safe to call defensively (zero agent calls when nothing changed) - the property the MCP surface depends on |
| Ingest skips re-parsing a file whose mtime+size match the previous run | Parsing 48 PDFs/DOCX/ODT isn't free either; `ingest_documents(..., previous=...)` reuses the cached `RawDocument` for unchanged files, so only new/edited CVs pay the extraction cost |
| cv-pal is consumed as an MCP server (stdio) - the primary interface, not a secondary mode | Explicit user requirement: cv-pal must be a programmatic tool any AI agent (opencode today, Claude Code, others later) can call the way they already call engram, not just a CLI pipeline a human runs. Implemented with the official `mcp` SDK's `FastMCP` in `interfaces/mcp/server.py`, wired through the same `container.py`/use cases as the CLI - proof that hexagonal architecture pays for itself when a second interface adapter is genuinely free to add |
| The host agent drafts the CV/cover letter; cv-pal never runs a nested LLM call for it | Only `rebuild_knowledge_base` calls the configured backend agent (batch extraction). The `cv_pal` MCP prompt assembles material + protocol and lets the *host's own model* write and print the document - avoids paying for two models on the hot path, and lets the user iterate ("shorter", "emphasize fintech") for free in the host's own context instead of round-tripping to cv-pal |
| `/cv-pal` is a single-call, one-shot prompt (not a suite of granular fetch tools the host must orchestrate) | Minimizes round-trips and token cost: one call assembles knowledge base + posting + protocol; the host does everything else (draft, print, ask about a cover letter, iterate) in its own context without calling back into cv-pal. Granular tools (`get_cv_material`, `get_knowledge_base`) still exist for inspection/editing, but aren't the default path |
| Agent-facing material is a stripped "lean view" (`application/services/agent_view.py`), not the full markdown file | The full `data/knowledge-base.md` carries `source_files` provenance and superseded personal-data variants (`(previous)` phone/LinkedIn/GitHub) - dead weight for an agent drafting a CV. Stripping both cuts the material roughly in half without touching anything an agent could plausibly want to select from (every summary variant, every experience bullet, every skill, every distinct headline phrasing stay) |
| Document rendering (`.docx`/`.pdf`) needs no agent - it's a local, deterministic operation | `infrastructure/rendering/local_document_renderer.py` converts markdown with `python-docx` directly, and goes through a temp `.docx` + `soffice --headless --convert-to pdf` for PDF. The project previously assumed Anthropic Agent Skills were required for this (see the old, since-corrected Decision Log entry about opencode's capabilities) - LibreOffice was already installed on this machine the whole time |
| Fetching a job posting by URL needs no agent either - `WebContentPort` is a plain HTTP adapter, same reasoning as document rendering | `infrastructure/web_content/http_web_content.py` (`HttpWebContent`) fetches the page with `urllib.request` and strips it to readable text with a stdlib `html.parser.HTMLParser` (no new HTTP/HTML dependency). Wired via `container.web_content` into `UrlJobPostingSource`, used by both `cvpal tailor --job-url` and the MCP `cv_pal` prompt's `job_posting_url` argument. Not a general-purpose readability extractor - strips `<script>`/`<style>`/`<head>` and every tag, good enough to hand a job posting's body text to a tailoring prompt. Fetch/parse failures raise `JobPostingFetchError`, surfaced as a plain message to the host agent rather than a stack trace |
| Cover-letter drafting is conversational, not a fire-and-forget generation call | Explicit user requirement: the host must ask before writing a cover letter, and either elicit the user's voice (no profile captured yet: ask for tone, offer an example opener, or ask what to highlight) or confirm the already-captured voice profile's essence before writing - `application/prompts/cv_pal.py` encodes this branch directly in the assembled prompt |
| `update_knowledge_base` rejects an apparent near-total wipe unless `force=True` | The markdown parser is deliberately tolerant (a design goal for hand edits), which means "does it parse" is not a strong safety check - garbage input still parses, into a mostly-empty `KnowledgeBase`. `application/use_cases/update_knowledge_base.py` compares record counts before/after and refuses a drop past a retention threshold, backing up the previous file regardless |
| Multi-user is a parameter, not implemented - the project maintainer's own CVs are the test fixture | The user's explicit direction: design every new piece to receive the knowledge base/paths as data, never hardcode an identity. `markdown_knowledge_repository.py`'s header, `personal_data_resolution.py`'s `PREFERRED_VALUES`, and `output_naming.py`'s user slug now read from `CVPAL_USER_NAME`/`CVPAL_PHONE`/`CVPAL_LINKEDIN`/`CVPAL_GITHUB`/`CVPAL_USER_SLUG` env vars (fictitious defaults) rather than a hardcoded name - an interim escape valve ahead of the real per-user config file (`~/.config/cvpal/config.toml`, see PROJECT_STATUS); `config.Settings` paths aren't yet namespaced per user either |
| v1 targets only opencode and Claude Code, both over stdio - no HTTP/SSE, no ChatGPT/Pi | ChatGPT's MCP support is remote-connector-only (Pro/Business gated) and Pi has no known MCP support - both would need a different transport and auth model, deliberately out of scope until there's a concrete need |
| Engram consulted every session, on this maintainer's machine | Not a project requirement - a personal workflow preference of whoever is developing this particular checkout. Contributors without engram (or any persistent-memory tool) configured skip that step entirely, see Agent Startup Protocol above |

---

## Context Files

Read these files when starting or resuming work:

| File | When to Read |
|------|--------------|
| `AGENTS.md` | Always |
| `PROJECT_STATUS.md` | Always |
| `skills/{name}/SKILL.md` | Before touching that concern area |

---

## Current Status

See `PROJECT_STATUS.md` for implementation progress.
