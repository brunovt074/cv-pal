# CV-Pal — Project Status

## Vision

Consolidate ~50 scattered CV/cover-letter documents (PDF/DOCX/ODT, multiple stacks: Java, PHP,
C#, JS, Python) into a single English-language knowledge base, then use that base to generate
100%-tailored CVs and cover letters per job posting, and assisted drafts for freelance platform
profiles — all in Bruno's own writing voice, via an agent-agnostic core (opencode today, any
other agent tomorrow).

---

## Technology Stack

| Component | Choice |
|-----------|--------|
| Language | Python 3.12 |
| Architecture | Hexagonal (ports & adapters) — see `AGENTS.md` |
| AI engine | Provider-agnostic `TextCompletionPort`. Default adapter: `opencode` CLI, model `opencode-go/deepseek-v4-pro`. Second adapter (Claude Code CLI) exists to prove the abstraction |
| Document parsing | pdfplumber (+ hyperlink extraction), python-docx, odfpy, `pdftotext -layout` fallback |
| Knowledge base | `data/knowledge-base.md` (source of truth) + optional `data/cv-knowledge-base.xlsx` export |
| Data / sheet export | pandas, openpyxl |
| Sheets sync | gspread + service account (not yet implemented) |
| Document generation (`.docx`/`.pdf`) | Not yet wired — needs a `DocumentRenderPort` adapter |
| API / CLI | FastAPI (planned) + Typer (`src/cvpal/interfaces/cli/`) |

See `AGENTS.md`'s Architecture section for the layer breakdown and the agent-agnosticism
mechanism, and its Decision Log for the reasoning behind each choice below.

---

## Development Rules

- No comments in production code
- English identifiers; knowledge base content in English (translated on-the-fly at tailoring time)
- Type hints + pydantic models at every module boundary
- `domain` has zero infrastructure imports; `application` depends only on `domain`; only
  `container.py` wires infrastructure adapters to use cases
- Feature branch workflow only, never commit to `master`

---

## Branch Chain Strategy

Current chain:

```
master
  <- feature/initial-config
      <- feature/data-pipeline        (ingest + legacy .xlsx analytics — superseded by below)
          <- feature/hexagonal-agents (current — ports & adapters, agent-agnostic core,
                                        markdown KB, voice profile, tailoring)
```

### Branch Intent

- `master`: empty baseline
- `feature/initial-config`: scaffold, `AGENTS.md`, `PROJECT_STATUS.md`, skills, governance layer
- `feature/data-pipeline`: original ingestion + `.xlsx`-centric analytics (MVP v1) — kept in
  history, its ingestion logic was carried forward, its analytics/knowledge modules were replaced
- `feature/hexagonal-agents` (current): full hexagonal restructure; provider-agnostic agent
  layer (`CliAgentSpec` + registry); `data/knowledge-base.md` as the new source of truth
  (personal data, summary, experience, education, certifications, skills, projects, languages,
  voice profile — voice extraction folded in, no separate stage); CV tailoring against a job
  posting given as text or a local file
- `feature/generation-engine` (next): a `DocumentRenderPort` adapter for real `.docx`/`.pdf`
  output, and a `WebContentPort` adapter so job postings can be given by URL
- `feature/freelance-profiles` (after): assisted profile drafts per platform
- `feature/web-job-search` (future iteration): autonomous job search via web search / scheduled
  agents

---

## Current State

### Hexagonal restructure + agent-agnostic core [COMPLETE]
**Branch**: `feature/hexagonal-agents`

- `domain/`: pydantic models (`documents`, `knowledge`, `jobs`, `generation`), ports as
  `typing.Protocol` (`text_completion`, `document_render`, `web_content`,
  `knowledge_repository`, `raw_document_repository`, `document_parser`, `job_posting_source`,
  `checkpoint_store`), `Capability` enum, error hierarchy.
- `infrastructure/agents/`: `CliAgentSpec` (declarative shape for any subprocess-driven agent) +
  one generic `CliAgentAdapter`. Two concrete specs: `opencode` (default) and `claude-code`
  (proves the abstraction generalizes). Registry + `container.py` resolve the active provider
  from `CVPAL_AGENT` and fail fast (`CapabilityNotSupportedError`) if it lacks a capability a use
  case needs.
- `infrastructure/parsers/`: PDF/DOCX/ODT extraction + section detection, moved from the original
  `ingest/` package with zero logic changes (all bugs fixed there previously — layout-aware
  whitespace ratio, double-spaced header collapsing — carried forward intact).
- `infrastructure/persistence/`: `MarkdownKnowledgeRepository` (the new source-of-truth
  read/write), `JsonRawDocumentRepository`, `FileCheckpointStore`, `XlsxExporter` (optional
  secondary export), `cv_version_inventory` (deterministic, feeds the xlsx export only).
- **Result on the real corpus**: `cvpal ingest` against `/home/br1/cv/` still gets 48/48 source
  files, 0 extraction warnings, 0 undetected languages — the parser move didn't regress anything.
- 79 tests (up from 33), all pure/deterministic or backed by a `FakeTextAgent` — zero live LLM
  calls in the automated suite. `ruff check` clean.

### Knowledge base build [COMPLETE, verified against the real corpus]
**Branch**: `feature/hexagonal-agents`

- `application/use_cases/build_knowledge_base.py`: one agent call per canonical section
  (personal_data, summary, experience, education+certifications, skills, projects, languages,
  voice_profile), each returning JSON validated against a `domain/knowledge/models.py` model —
  never markdown text directly. Checkpointed per section (`data/.checkpoints/`) so a killed run
  resumes.
- `application/services/personal_data_resolution.py`: deterministic correction pass — which
  phone/LinkedIn/GitHub value is current is a hardcoded fact (confirmed by Bruno), never an
  agent guess. A real substring-matching bug was caught and fixed here during implementation
  ("bruno-vargas-tettamanti-dev" was matching inside "...-developer" via naive substring
  containment) — now compares normalized full identifiers.
- `infrastructure/persistence/markdown_knowledge_repository.py`: renders/parses
  `data/knowledge-base.md` as one markdown table per section + a free-form `Notes` section
  preserved verbatim across rebuilds. Tolerant of hand-added rows on reload.
- `application/use_cases/audit_knowledge_base.py` + `cvpal kb audit`: reports personal-data
  fields with more than one distinct value, so the correction pass's output is visible, not just
  silently applied.
- **Run against the real corpus** (`/home/br1/cv/`, via the `opencode` adapter): produced
  `data/knowledge-base.md` covering personal data (name/phone/email/location/headline/
  LinkedIn/GitHub/projects/portfolio links, with the known-current phone `+5493772566242`,
  LinkedIn `bruno-vargas-tettamanti-dev`, and GitHub `brunovt074` correctly tagged `(current)`
  against older variants tagged `(previous)`), summary variants, experience bullets, education,
  certifications, skills, projects, languages, and a voice profile extracted from the cover
  letters. One known pre-existing extraction artifact (a UTN certificate URL, corrupted by two
  concatenated links in the source PDF) was deferred, not silently fixed — flagged for a manual
  pass later.

### CV tailoring [COMPLETE for text/file postings; URL and real-document output deferred]
**Branch**: `feature/hexagonal-agents`

- `application/use_cases/tailor_cv.py` + `application/prompts/tailoring.py`: given a job posting
  and the knowledge base markdown, produces a tailored CV in markdown, selecting only relevant
  material (never fabricating), in a language inferred from the posting (or overridden).
- `infrastructure/job_postings/`: `InlineTextJobPostingSource` (`--job-text`),
  `FileJobPostingSource` (`--job-file`, `.txt`/`.md`/`.docx`), `UrlJobPostingSource` (raises
  `CapabilityNotSupportedError` until a `WebContentPort` adapter exists — not opencode's fault
  per se, see `AGENTS.md`).
- `cvpal tailor` CLI command wires it end-to-end, writing to `data/outputs/`.
- **Not yet implemented**: real `.docx`/`.pdf` output (needs `DocumentRenderPort`), job posting
  by URL (needs `WebContentPort`), a separate cover-letter use case.

### Not started
- Google Sheets sync (small addition, can be picked up anytime)
- `DocumentRenderPort` + `WebContentPort` adapters (Fase: `feature/generation-engine`)
- Cover-letter tailoring (mirrors `tailor_cv.py`)
- Freelance profiles
- Web job search (future iteration)

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
cvpal ingest              # re-parse all source docs (fast, no agent calls)
cvpal kb build            # extract + validate + render data/knowledge-base.md (calls the configured agent)
```

`kb build` may need to be re-run if killed by an external time limit — it resumes from
`data/.checkpoints/` automatically. Delete that directory to force a full recompute (e.g. after
changing an extraction prompt).

## Tailoring a CV

```bash
cvpal tailor --job-text "Backend Java developer, Spring Boot, remote"
cvpal tailor --job-file /path/to/posting.docx --language es
```

## Switching agent provider

```bash
export CVPAL_AGENT=claude-code   # or opencode (default)
cvpal agents list                # see what's registered
cvpal agents check                # round-trip a trivial prompt against the active one
```

---

## Next Actions

1. `DocumentRenderPort` adapter (Anthropic SDK + Agent Skills, or another mechanism) for real
   `.docx`/`.pdf` tailored output — first real use of a non-CLI agent in this project.
2. `WebContentPort` adapter so job postings can be given by URL.
3. Fix the UTN certificate URL extraction artifact in `data/knowledge-base.md` (deferred, not
   blocking).
4. Optionally: Google Sheets sync from the `.xlsx` export, if useful for manual review.
5. Cover-letter tailoring use case, freelance profiles, web job search — in that order per the
   branch chain above.
