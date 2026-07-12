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
  <- feature/initial-config   (current)
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

### Scaffold [IN PROGRESS]
**Branch**: `feature/initial-config`

**Completed**:
- Directory structure (`src/cvpal/`, `skills/`, `data/`, `tests/`)
- `pyproject.toml`, `.gitignore`, `.env.example`
- `AGENTS.md`, `PROJECT_STATUS.md`

**Next in this branch**:
- `CLAUDE.md`, `README.md`
- `skills/*/SKILL.md` for all 7 skills
- `git init` + first commit

### Not started
- Ingestion pipeline (Fase 1)
- Analytics + workbook builder (Fase 2) — produces the MVP deliverable `cv-knowledge-base.xlsx`
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
