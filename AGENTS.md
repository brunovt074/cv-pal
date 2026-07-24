# CV-Pal — Agent Guidelines

> Single Source of Truth for all AI coding agents working on this project.
> Compatible with: Claude Code, Codex, Cursor, Windsurf, Gemini CLI, Copilot, Aider, Junie.

---

## Agent Startup Protocol

Before writing any code, every agent MUST:

1. Read this file completely
2. Read `PROJECT_STATUS.md` to understand current state and branch chain
3. Query engram (`mem_search` / `mem_context`) for prior decisions on this project
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
| Purpose | Consolidate ~50 CV/cover-letter documents into a single knowledge base, then generate tailored CVs, cover letters, and freelance-platform profiles per job posting |
| Architecture | Hexagonal (ports & adapters) — see below. Pipeline (ingest → build knowledge base) + generation (tailoring) |
| Knowledge base | `data/knowledge-base.md` — source of truth, versioned in git, editable by a human or any agent. `data/cv-knowledge-base.xlsx` is an optional secondary export, not authoritative |
| AI engine | Provider-agnostic by design — see Architecture. Default today: `opencode` CLI, model `opencode-go/deepseek-v4-pro`. A second CLI adapter (Claude Code) already exists to prove the abstraction holds |
| API + CLI | FastAPI (planned) + Typer CLI (`src/cvpal/interfaces/cli/`) |

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
| Application | `src/cvpal/application/` | Use cases (`use_cases/`), prompt templates (`prompts/`), pure services (`services/` — dedupe, checkpointing helpers, response parsing, personal-data correction). Depends only on `domain` |
| Infrastructure | `src/cvpal/infrastructure/` | Port implementations: `agents/` (CLI-driven text-completion adapters), `parsers/` (PDF/DOCX/ODT extraction), `persistence/` (markdown/JSON/xlsx repositories, checkpoint store), `job_postings/` (text/file/URL sources) |
| Interfaces | `src/cvpal/interfaces/cli/` | Typer entry point. Resolves everything through `container.py` |

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
Today only `TEXT_COMPLETION`/`JSON_COMPLETION` are wired to any adapter; `DOCUMENT_RENDER`
(real `.docx`/`.pdf` output) and `WEB_CONTENT` (fetching a job posting URL) have ports defined
but no adapter yet — see `skills/cv-generation/SKILL.md`'s "Not yet wired" section, and do not
assume opencode categorically can't do these (it has a native `webfetch` tool and MCP support;
the actual blocker is non-interactive `run` mode auto-denying tool permissions).

### Component Layout

| Component | Location | Purpose |
|-----------|----------|---------|
| Domain models & ports | `src/cvpal/domain/` | Data shapes + boundary contracts, no I/O |
| Ingestion | `src/cvpal/infrastructure/parsers/`, `application/use_cases/ingest_documents.py` | Extract structured data from PDF/DOCX/ODT source documents |
| Knowledge base build | `application/use_cases/build_knowledge_base.py`, `application/prompts/`, `infrastructure/persistence/markdown_knowledge_repository.py` | Dedupe, extract via agent, validate, render `data/knowledge-base.md` |
| Tailoring | `application/use_cases/tailor_cv.py`, `infrastructure/job_postings/` | Generate a CV tailored to one job posting |
| Agent layer | `src/cvpal/infrastructure/agents/`, `src/cvpal/container.py` | Provider-agnostic text-completion adapters + composition root |
| CLI | `src/cvpal/interfaces/cli/main.py` | Typer entry point (`cvpal` console script) |
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
cvpal ingest                          # Parse all source docs (CV_RAW_DIR) into data/ingested.json
cvpal kb build                        # Build/refresh data/knowledge-base.md from ingested.json
cvpal kb audit                        # Report personal-data fields with multiple distinct values
cvpal tailor --job-text "..."         # Generate a tailored CV from a job posting given as text
cvpal tailor --job-file posting.docx  # ...or from a local .txt/.md/.docx file
cvpal agents list                     # List registered agent providers
cvpal agents check                    # Round-trip a trivial prompt against the configured agent
```

Not yet implemented: `cvpal sync` (Google Sheets), `cvpal profile <platform>` (freelance
profiles), real `.docx`/`.pdf` tailored output, job-posting-by-URL.

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
              <- feature/generation-engine   (DocumentRenderPort adapter: real .docx/.pdf output)
                  <- feature/freelance-profiles
                      <- feature/web-job-search   (future iteration; needs a WebContentPort adapter)
```

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
| `cv-generation` | `skills/cv-generation/SKILL.md` | `application/use_cases/tailor_cv.py`, `application/prompts/tailoring.py`, `infrastructure/job_postings/`, `infrastructure/agents/` |
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
| Adding a `DocumentRenderPort` or `WebContentPort` adapter | `cv-generation` |
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
| `data/knowledge-base.md` replaces `.xlsx` as the source of truth | Decided in an earlier analysis pass, reconfirmed this session: any agent reads markdown natively without a parsing step; a human can hand-edit it directly and diff it in git. The `.xlsx` export (`infrastructure/persistence/xlsx_exporter.py`) is kept as an optional secondary output for spreadsheet review, not authoritative |
| Extraction prompts return JSON validated against domain models, never markdown text directly | A deterministic renderer (`markdown_knowledge_repository.save()`) turns the validated `KnowledgeBase` into markdown afterward. This makes `build_knowledge_base()` testable with a scripted `FakeTextAgent` and no live LLM call, and guarantees the file's shape regardless of how faithfully an agent follows formatting instructions |
| Markdown knowledge base uses per-field tables + a free-form `Notes` section, not bespoke prose formatting per section type | One generic table renderer/parser works for every record-based section (`PersonalDataField`, `ExperienceBullet`, `SkillEntry`, ...) — far less code than a bespoke parser per section, and just as human-editable. `Notes` is preserved verbatim across `cvpal kb build` reruns for anything that doesn't fit a table row |
| Which personal-data value is "current" (phone, LinkedIn, GitHub) is a hardcoded fact, never an LLM guess | `application/services/personal_data_resolution.py` applies known-authoritative values as a deterministic post-processing pass. An agent extracts all distinct values found across the corpus; only a human can say which one is real. Caught a real substring-matching bug here during implementation ("-dev" matching inside "-developer") — covered by `tests/application/test_personal_data_resolution.py` against the actual corpus's known-inconsistent values |
| Knowledge base content in English by default | Avoids maintaining ES/EN duplicates; translation happens on-the-fly per job application at tailoring time |
| Voice/tone extracted from existing cover letters, as one section of the same knowledge-base build pass | The letters are the ground truth for "sounding like him" — no separate interview or pipeline stage needed |
| Freelance profiles = human-in-the-loop | Upwork/Fiverr ToS prohibit account automation; agent generates content, human pastes/reviews. API automation only where a real API exists (e.g. Himalayas/boards) |
| Text-generation tasks go through a `TextCompletionPort`, default adapter `opencode` CLI (`opencode-go/deepseek-v4-pro`) | Explicit user decision. `infrastructure/agents/cli/opencode.py` shells out to the already-authenticated `opencode` CLI instead of reading its credential store directly. A second adapter (`cli/claude_code.py`, Claude Code CLI) exists specifically to prove the `CliAgentSpec` abstraction generalizes beyond opencode, not just in theory |
| Per-section agent calls, not one giant call | A single call covering all CV sections at once triggers unreliable behavior in non-interactive CLI agent modes: tool-call permissions are auto-denied, so a large response the model tries to write to a scratch file silently produces empty output. Splitting into one small call per canonical section (personal_data, summary, experience, education+certifications, skills, projects, languages, voice_profile) keeps outputs small enough to return reliably |
| `source_files` capped at 3 representative files per record | Uncapped lists blew up JSON output size for near-universal facts (e.g. a skill appearing in 30+ of 38 CVs), truncating the response mid-string. Traceability doesn't need every duplicate, just a representative sample |
| Checkpoint every agent-backed structuring step to disk | Individual pipeline runs can exceed a harness's background-execution time limit; checkpointing each step's result (`data/.checkpoints/`, gitignored, via `CheckpointStorePort`) lets `cvpal kb build` be re-run in short bursts, resuming instead of re-paying completed calls |
| Engram consulted every session | Persistent memory protocol is globally active; always `mem_search`/`mem_context` at start, `mem_save` after decisions |

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
