# CV-Pal — Project Status

## Vision

Consolidate ~50 scattered CV/cover-letter documents (PDF/DOCX/ODT, multiple stacks: Java, PHP,
C#, JS, Python) into a single English-language knowledge base spreadsheet, then use that base to
generate 100%-tailored CVs and cover letters per job posting, and assisted drafts for freelance
platform profiles — all in Bruno's own writing voice.

---

## Technology Stack

| Component | Choice |
|-----------|--------|
| Language | Python 3.12 |
| AI | Anthropic Python SDK, `claude-opus-4-8`, adaptive thinking |
| Document parsing | pdfplumber, python-docx, odfpy, LibreOffice headless fallback |
| Data / sheet | pandas, openpyxl |
| Sheets sync | gspread + service account |
| Document generation | Claude Agent Skills (`docx`/`pdf`) via code execution container |
| API / CLI | FastAPI + Typer |

---

## Development Rules

- No comments in production code
- English identifiers; knowledge base content in English (translated on-the-fly at generation time)
- Type hints + pydantic models at every module boundary
- Feature branch workflow only, never commit to `master`

---

## Branch Chain Strategy

Current chain:

```
master
  <- feature/initial-config
      <- feature/data-pipeline   (current)
```

### Branch Intent

- `master`: empty baseline
- `feature/initial-config`: scaffold, AGENTS.md, PROJECT_STATUS.md, skills, governance layer
- `feature/data-pipeline` (next): ingestion + analytics + knowledge base workbook (the MVP deliverable)
- `feature/voice-profile` (after): style guide extraction from cover letters
- `feature/generation-engine` (after): CV/cover-letter tailoring per job posting
- `feature/freelance-profiles` (after): assisted profile drafts per platform
- `feature/web-job-search` (future iteration): autonomous job search via web search / scheduled agents

---

## Current State

### Scaffold [COMPLETE]
**Branch**: `feature/initial-config` (merged into chain, not yet into `master`)

- Directory structure, `pyproject.toml`, `.gitignore`, `.env.example`
- `AGENTS.md`, `PROJECT_STATUS.md`, `CLAUDE.md`, `README.md`
- All 7 `skills/*/SKILL.md`
- `.engram/config.json` (`project_name: cv-pal`) so future sessions resolve engram without
  ambiguity — this session's MCP server cwd is fixed at `/home/br1/cv` (ambiguous: two git
  children `cv/`, `php/`), so engram memory could not be written under `cv-pal` this run

### Ingestion [COMPLETE]
**Branch**: `feature/data-pipeline`

- `src/cvpal/ingest/`: PDF (pdfplumber + `pdftotext -layout` fallback), DOCX (python-docx), ODT
  (odfpy) extractors, dispatched by extension in `ingest_all()`.
- Section detection (`sections.py`) via ES/EN keyword matching on header lines; language
  detection via header keywords with a stopword-ratio fallback for header-less prose (cover
  letters).
- **Result on the real corpus**: 48/48 source files ingested with zero crashes, 0 extraction
  warnings, 0 undetected languages. 37/38 CVs got full section coverage (summary, experience,
  education, skills, languages); 1 CV has no section headers at all in its source layout and
  correctly falls back to the `unstructured` bucket (nothing lost, flagged for analytics to
  handle via LLM parsing in Fase 2).
- Fixed two real bugs found during verification: (1) `pdfplumber(layout=True)` pads output with
  large whitespace runs that broke the alpha-ratio "garbled text" heuristic and the
  LibreOffice-as-txt-converter fallback (LibreOffice treats standalone PDFs as Draw documents and
  fails to save as text) — replaced with `pdftotext -layout` and a whitespace-aware ratio; (2)
  `layout=True` sometimes double-spaces header text ("Resumen  Profesional"), breaking substring
  keyword matching — fixed by collapsing whitespace runs before comparing.
- 18 tests (`tests/test_sections.py`, `tests/test_ingest.py`), including integration tests
  against 5 real fixture files copied into `tests/fixtures/`. `ruff check` clean.
- CLI: `python -m cvpal.cli` (single Typer command, no subcommand name needed yet) runs the full
  ingest and writes `data/ingested.json` (gitignored — regenerable build artifact).

### Not started
- Data Analytics + workbook builder (Fase 2) — **next up, produces the MVP deliverable**
  `data/cv-knowledge-base.xlsx` (committed to git per the Decision Log — it is the source of
  truth, not a build artifact)
- Voice profile extraction (Fase 3)
- Generation engine (Fase 4)
- Freelance profiles (Fase 5)
- Web job search (Fase 6, future)

---

## Validation Commands

```bash
pip install -e ".[dev]"
ruff check src tests
pytest
```

---

## Next Actions

1. Finish governance layer (CLAUDE.md, README.md, all SKILL.md files)
2. `git init`, first commit on `master`, branch to `feature/initial-config`
3. Start Fase 1: document ingestion (PDF/DOCX/ODT → normalized pydantic records)
4. Fase 2: build `cv-knowledge-base.xlsx` — this is the requested deliverable, prioritize it
