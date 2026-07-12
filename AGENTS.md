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
| Purpose | Consolidate ~50 CV/cover-letter documents into a single knowledge base spreadsheet, then use Claude to generate tailored CVs, cover letters, and freelance-platform profiles |
| Architecture | Pipeline (ingest → analytics → knowledge base) + agent layer (tailoring, voice, profiles) |
| Knowledge base | `.xlsx` (source of truth, versioned in git) + Google Sheets sync |
| AI engine (text tasks) | `opencode` CLI subprocess, model `opencode-go/deepseek-v4-pro` — see Decision Log |
| AI engine (document generation, Fase 4) | Anthropic Python SDK, `claude-opus-4-8` — Agent Skills/`web_fetch` have no opencode equivalent |
| API + CLI | FastAPI + Typer CLI |

### Component Layout

| Component | Location | Purpose |
|-----------|----------|---------|
| Ingestion | `src/cvpal/ingest/` | Extract structured data from PDF/DOCX/ODT source documents |
| Analytics | `src/cvpal/analytics/` | Dedupe, normalize, translate to English, consolidate |
| Knowledge | `src/cvpal/knowledge/` | Build the `.xlsx` workbook; sync to Google Sheets |
| Voice | `src/cvpal/voice/` | Extract a style guide from existing cover letters |
| Agents | `src/cvpal/agents/` | CV tailoring, cover letters, freelance profiles, job search |
| LLM | `src/cvpal/llm/` | `opencode` CLI subprocess wrapper (text tasks); Anthropic client for Fase 4 doc generation |
| API | `src/cvpal/api/` | FastAPI endpoints |
| CLI | `src/cvpal/cli.py` | Typer entry point |
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

## CLI Commands (once implemented)

```bash
cvpal ingest              # Parse all source docs into normalized JSON
cvpal build-sheet         # Build data/cv-knowledge-base.xlsx from ingested data
cvpal sync                # Push the workbook to Google Sheets
cvpal voice               # Extract voice-profile.md from cover letters
cvpal tailor <job-url>    # Generate a tailored CV + cover letter for a job posting
cvpal profile <platform>  # Generate a freelance-platform profile draft
```

---

## Code Style

- No comments in production code — naming and structure must explain intent
- Code identifiers (functions, classes, variables, files, packages) in English
- **Knowledge base content is English by default** — see Decision Log. Translation to another
  language happens only at generation time (Fase 4), never stored as a duplicate in the sheet
- Type hints on all public functions; pydantic models for all structured data crossing a
  module boundary (ingest output, workbook rows, LLM tool schemas)
- One class/dataclass per concern; no god-objects for "the CV"
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
      <- feature/data-pipeline        (ingest + analytics + knowledge base)
          <- feature/voice-profile
              <- feature/generation-engine
                  <- feature/freelance-profiles
                      <- feature/web-job-search   (future iteration)
```

---

## Skills

### Available Skills

| Skill | File | Scope |
|-------|------|-------|
| `data-extraction` | `skills/data-extraction/SKILL.md` | ingest/ |
| `data-analytics` | `skills/data-analytics/SKILL.md` | analytics/, knowledge/ |
| `voice-style` | `skills/voice-style/SKILL.md` | voice/ |
| `cv-generation` | `skills/cv-generation/SKILL.md` | agents/, llm/ |
| `freelance-profiles` | `skills/freelance-profiles/SKILL.md` | agents/profile_builder.py |
| `qa-code` | `skills/qa-code/SKILL.md` | shared |
| `skill-creator` | `skills/skill-creator/SKILL.md` | skills/ |

### Auto-invoke Rules

| Action | Read This Skill |
|--------|------------------|
| Adding/modifying a document parser (PDF/DOCX/ODT) | `data-extraction` |
| Changing dedupe/normalization/translation logic | `data-analytics` |
| Changing the workbook schema (tabs/columns) | `data-analytics` |
| Extracting or applying the voice/style guide | `voice-style` |
| Building CV/cover-letter tailoring prompts | `cv-generation` |
| Wiring Agent Skills (`docx`/`pdf`/`xlsx`) or server tools | `cv-generation` |
| Generating a freelance platform profile | `freelance-profiles` |
| Running code quality audits or refactors | `qa-code` |
| Creating a new skill | `skill-creator` |

---

## Decision Log

Architectural decisions made — do not relitigate without strong evidence:

| Decision | Rationale |
|----------|-----------|
| Full app (not just Sheets + Claude web) | Historias 3-4 need real code: platform integrations and web search can't run from Claude web alone |
| `.xlsx` local + Google Sheets sync (both) | `.xlsx` is the git-versioned source of truth; Sheets is for manual review and API-driven agent consumption |
| Knowledge base content in English by default | Avoids maintaining ES/EN duplicates; translation happens on-the-fly per job application in Fase 4 |
| Voice/tone extracted from existing cover letters | Bruno's existing letters are the ground truth for "sounding like him" — no separate interview needed for MVP |
| Freelance profiles = human-in-the-loop | Upwork/Fiverr ToS prohibit account automation; agent generates content, Bruno pastes/reviews. API automation only where a real API exists (e.g. Himalayas/boards) |
| Text-generation tasks (translation, dedupe/structuring, voice extraction) go through the `opencode` CLI with `opencode-go/deepseek-v4-pro`, not the Anthropic SDK | Explicit user decision, confirmed twice after initial clarification. cv-pal shells out to the already-authenticated `opencode` CLI (`src/cvpal/llm/opencode_client.py`) instead of reading its credential store directly. **Anthropic's `claude-opus-4-8` remains the engine for Fase 4** (document generation via Agent Skills, `web_fetch` for job postings) — DeepSeek/opencode has no equivalent for those Anthropic-specific server tools |
| Per-section LLM calls, not one giant call | A single call covering all CV sections at once triggered unreliable behavior in the opencode harness: tool-call permissions are auto-denied in non-interactive `run` mode, so a large JSON response the model tried to write to a scratch file silently produced empty output. Splitting into one small call per canonical section (personal_data, summary, experience, education+certifications, skills, projects, languages) keeps outputs small enough to return as plain chat text reliably |
| `source_files` capped at 3 representative files per record | Uncapped lists blew up JSON output size for near-universal facts (e.g. a skill appearing in 30+ of 38 CVs), truncating the response mid-string. Traceability doesn't need every duplicate, just a representative sample |
| Checkpoint every LLM structuring step to disk | Individual pipeline runs can exceed the harness's background-execution time limit; checkpointing each step's result (`data/.checkpoints/`, gitignored) lets `cvpal build-sheet` be re-run in short bursts, resuming instead of re-paying completed LLM calls |
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
