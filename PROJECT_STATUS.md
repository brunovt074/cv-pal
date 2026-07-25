# CV-Pal — Project Status

## Vision

A programmatic, agent-agnostic CV/cover-letter tailoring tool - consumed by AI agents (opencode,
Claude Code) over MCP the same way they consume engram, not a pipeline a human runs by hand.
Consolidates ~50 scattered CV/cover-letter documents (PDF/DOCX/ODT, multiple stacks: Java, PHP,
C#, JS, Python) into a single English-language knowledge base, then any host agent tailors a CV
and cover letter to a job posting from it - conversationally, in the author's voice, using only
real material. Bruno is the test fixture; the design deliberately treats the user as a parameter,
not a hardcoded assumption, for future multi-user use.

---

## Technology Stack

| Component | Choice |
|-----------|--------|
| Language | Python 3.12 |
| Architecture | Hexagonal (ports & adapters) — see `AGENTS.md` |
| Primary interface | MCP server over stdio (`cvpal serve-mcp`), via the official `mcp` SDK (`FastMCP`) |
| Secondary interface | Typer CLI (`src/cvpal/interfaces/cli/`) |
| AI engine | Provider-agnostic `TextCompletionPort`. Default adapter: `opencode` CLI, model `opencode-go/deepseek-v4-pro`. Second adapter (Claude Code CLI) exists to prove the abstraction. Only used by `rebuild_knowledge_base` - the primary MCP flow drafts documents with the *host's* model, no nested LLM call |
| Document parsing | pdfplumber (+ hyperlink extraction), python-docx, odfpy, `pdftotext -layout` fallback |
| Knowledge base | `data/knowledge-base.md` (source of truth) + optional `data/cv-knowledge-base.xlsx` export |
| Document rendering | `python-docx` + `soffice --headless` (local, no agent/API key needed) |
| Data / sheet export | pandas, openpyxl |
| Sheets sync | gspread + service account (not yet implemented) |

See `AGENTS.md`'s Architecture section for the layer breakdown, the MCP server contract, and the
Decision Log for the reasoning behind each choice below.

---

## Development Rules

- No comments in production code
- English identifiers; knowledge base content in English (translated on-the-fly at tailoring time)
- Type hints + pydantic models at every module boundary
- `domain` has zero infrastructure imports; `application` depends only on `domain`; only
  `container.py` wires infrastructure adapters to use cases — both `interfaces/cli/` and
  `interfaces/mcp/` follow the same rule
- Feature branch workflow only, never commit to `master`

---

## Branch Chain Strategy

Current chain:

```
master
  <- feature/initial-config
      <- feature/data-pipeline        (ingest + legacy .xlsx analytics — superseded)
          <- feature/hexagonal-agents (ports & adapters, agent-agnostic core, markdown KB, tailoring)
              <- feature/mcp-server    (current — MCP server as primary interface, local document
                                        renderer, content-addressed incremental checkpointing,
                                        lean agent view)
```

### Branch Intent

- `master`: empty baseline
- `feature/initial-config`: scaffold, `AGENTS.md`, `PROJECT_STATUS.md`, skills, governance layer
- `feature/data-pipeline`: original ingestion + `.xlsx`-centric analytics (MVP v1) — superseded
- `feature/hexagonal-agents`: full hexagonal restructure; provider-agnostic agent layer;
  `data/knowledge-base.md` as source of truth; CLI-driven CV tailoring
- `feature/mcp-server` (current): cv-pal as an MCP server consumed by opencode/Claude Code, the
  primary interface going forward; local `.docx`/`.pdf` rendering (no agent needed); incremental
  orchestration (ingest skips unchanged files, knowledge-base sections are only recomputed when
  their input actually changed); lean agent-facing knowledge base view. Folds in what was
  previously planned as `feature/generation-engine`
- `feature/freelance-profiles` (next): assisted profile drafts per platform
- `feature/web-job-search` (future iteration): autonomous job search via web search / scheduled
  agents

---

## Current State

### MCP server [COMPLETE, verified live from opencode and Claude Code]
**Branch**: `feature/mcp-server`

- `interfaces/mcp/server.py`: `cvpal serve-mcp` starts an MCP server over stdio. One prompt
  (`cv_pal`) + six tools (`get_cv_material`, `get_knowledge_base`, `update_knowledge_base`,
  `audit_knowledge_base`, `ingest_corpus`, `rebuild_knowledge_base`, `render_document`). Every
  handler is a thin wrapper around a `_verb(container, ...)` function, tested directly with a
  `Container` over a tmp dir (no MCP protocol, no live agent) — see
  `tests/interfaces/test_mcp_server.py`.
- **Design**: the host agent drafts and prints the CV/cover letter itself; cv-pal never runs a
  nested LLM call for it. Only `rebuild_knowledge_base` calls the configured backend agent.
- **Live verification**: registered in both `opencode mcp list` and `claude mcp list` (both show
  `connected`). Drove real tailoring requests through both clients against the real corpus:
  - **opencode** (`opencode run --auto`, DeepSeek backend model) called `get_cv_material`,
    produced a Java/Spring Boot-focused CV correctly using real contact data (current phone,
    LinkedIn, GitHub) and real experience, nothing fabricated.
  - **Claude Code** (`claude -p --allowedTools mcp__cvpal__get_cv_material`) called the same tool
    for a different posting (PHP/Laravel/fintech) and produced a CV selecting a *different* real
    subset of experience/skills appropriate to that posting — confirms selection, not templating.
  - **Finding**: both clients invoked cv-pal via the `get_cv_material` **tool** rather than the
    `cv_pal` **prompt** primitive when driven by a natural-language instruction in non-interactive/
    one-shot mode - MCP prompts may need an explicit slash-command-style invocation in an
    interactive session to be surfaced directly. The tool path already carries full value (real
    data, real selection, no fabrication); the `cv_pal` prompt's conversational protocol (cover
    letter branch, voice confirmation) needs an interactive session to observe end-to-end - not
    yet done, flagged as a follow-up manual check.
  - Claude Code also correctly asked for permission before calling `render_document` when it
    wasn't in `--allowedTools`, rather than silently failing or calling it anyway.

### Incremental orchestration [COMPLETE, verified against the real corpus]
**Branch**: `feature/mcp-server`

- `application/services/checkpointing.py`: checkpoints are content-addressed (fingerprint of a
  section's deduped input + a `PROMPT_VERSION` constant per prompt module), not existence-based.
  `application/use_cases/build_knowledge_base.py` returns a `KnowledgeBaseBuildReport` with
  `rebuilt_sections`/`skipped_sections`.
- `application/use_cases/ingest_documents.py`: skips re-parsing a file whose mtime/size match the
  previous ingest.
- **Measured on the real corpus** (`/home/br1/cv/`, 48 files): first `kb build` after this change
  rebuilt all 8 sections (old checkpoints were pre-fingerprint format, correctly treated as a
  miss) in the usual several minutes. Second consecutive `kb build` with no corpus changes: **0
  agent calls, 0.26s** (down from ~3 min/section). Second `ingest` with no changes: 48/48 files
  skipped, 0.25s (down from 2.3s). Touching one file's mtime without changing its content:
  re-parsed at the ingest layer, but the knowledge-base layer's content fingerprint still matched
  — zero agent calls, confirming the two-layer design (conservative mtime-based ingest cache,
  precise content-hash KB cache) works as intended, not just "changed vs unchanged file".

### Lean agent view [COMPLETE, measured on the real corpus]
**Branch**: `feature/mcp-server`

- `application/services/agent_view.py`: strips `source_files` provenance and `(previous)`-tagged
  personal-data variants; keeps every summary variant, experience bullet, skill, and distinct
  headline phrasing.
- **Measured**: full `data/knowledge-base.md` is 58,029 chars (~14.5K tokens); the lean view is
  25,704 chars (~6.4K tokens) — **44% of the original, a 56% reduction**. The assembled `cv_pal`
  prompt (lean view + a real posting + protocol) came to ~28.8K chars (~7.2K tokens) end to end.

### Local document rendering [COMPLETE]
**Branch**: `feature/mcp-server`

- `infrastructure/rendering/local_document_renderer.py`: markdown → `.docx` via `python-docx`
  directly; → `.pdf` via a temp `.docx` + `soffice --headless --convert-to pdf`. No agent, no API
  key - corrects an earlier assumption in this project that Anthropic Agent Skills were required.
- Wired into `cvpal tailor --format docx|pdf` and the MCP `render_document` tool.
- Tests generate a real PDF via `soffice` (skipped if not installed) and assert on `%PDF` magic
  bytes and non-empty output, plus a `.docx` reopened with `python-docx` and asserted on headings/
  bullets/bold.

### Knowledge base build [COMPLETE, verified against the real corpus]
**Branch**: `feature/hexagonal-agents` (content-addressed checkpointing added in `feature/mcp-server`)

- `application/use_cases/build_knowledge_base.py`: one agent call per canonical section, each
  returning JSON validated against a `domain/knowledge/models.py` model.
- `application/services/personal_data_resolution.py`: deterministic correction pass — which
  phone/LinkedIn/GitHub value is current is a hardcoded fact (confirmed by Bruno), never an agent
  guess. A real substring-matching bug was caught and fixed here during implementation.
- `infrastructure/persistence/markdown_knowledge_repository.py`: `render_markdown`/`parse_markdown`
  are now pure module functions (no I/O), reused by the repository and by
  `application/use_cases/update_knowledge_base.py` for host-initiated edits.
- **Current real-corpus numbers** (`/home/br1/cv/`, 48 files): 36 personal data fields, 7 summary
  variants, 50 experience bullets, 2 education entries, 2 certifications, 120 skills, 3 projects,
  3 languages, voice profile present. One known pre-existing extraction artifact (a UTN
  certificate URL, corrupted by two concatenated links in the source PDF) remains deferred.

### CV tailoring [COMPLETE for text/file postings; URL deferred]
**Branch**: `feature/hexagonal-agents`, extended in `feature/mcp-server`

- CLI path: `application/use_cases/tailor_cv.py` + `application/prompts/tailoring.py`, now with
  `--format markdown|docx|pdf`.
- MCP path (primary): `application/prompts/cv_pal.py` assembles the one-shot conversational
  prompt; the host agent drafts and prints the result.
- `infrastructure/job_postings/`: text, file (`.txt`/`.md`/`.docx`), URL (still raises
  `CapabilityNotSupportedError` — needs a `WebContentPort` adapter, not opencode's fault per se).
- **Not yet implemented**: job posting by URL, a standalone (non-conversational) cover-letter use
  case for the CLI path.

### Not started
- Google Sheets sync (small addition, can be picked up anytime)
- `WebContentPort` adapter for job-posting-by-URL
- Freelance profiles
- Web job search (future iteration)
- HTTP/SSE MCP transport (deliberately out of v1 scope — see Decision Log)

---

## Validation Commands

```bash
source .venv/bin/activate
ruff check src tests
pytest
```

## Rebuilding the knowledge base

```bash
source .venv/bin/activate
cvpal ingest              # re-parse changed source docs only (fast, no agent calls)
cvpal kb build            # recompute only sections whose input changed (calls the configured agent)
```

Both are safe to run any time — with no changes, `ingest` and `kb build` each finish in a fraction
of a second and make no agent calls. `kb build` still resumes from `data/.checkpoints/` if killed
mid-run; delete that directory to force a full recompute (e.g. after changing an extraction
prompt's wording without bumping its `PROMPT_VERSION`).

## Tailoring a CV (CLI)

```bash
cvpal tailor --job-text "Backend Java developer, Spring Boot, remote" --format pdf
cvpal tailor --job-file /path/to/posting.docx --language es --format docx
```

## Serving cv-pal to an agent (primary path)

```bash
cvpal serve-mcp
```

Client config in `skills/mcp-server/SKILL.md`. Verified connected in `opencode mcp list` and
`claude mcp list`.

## Switching agent provider

```bash
export CVPAL_AGENT=claude-code   # or opencode (default)
cvpal agents list                # see what's registered
cvpal agents check                # round-trip a trivial prompt against the active one
```

---

## Next Actions

1. Interactive verification of the `cv_pal` MCP *prompt* primitive itself (not just the
   `get_cv_material` tool) from an interactive opencode/Claude Code session, to confirm the
   cover-letter conversational branch (voice confirmation vs. elicitation) end to end.
2. `WebContentPort` adapter so job postings can be given by URL.
3. Fix the UTN certificate URL extraction artifact in `data/knowledge-base.md` (deferred, not
   blocking).
4. Optionally: Google Sheets sync from the `.xlsx` export, if useful for manual review.
5. A standalone cover-letter use case for the CLI path, freelance profiles, web job search — in
   that order per the branch chain above.
