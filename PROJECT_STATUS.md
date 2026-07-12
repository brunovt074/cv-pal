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
| AI (text tasks: translation, dedupe/structuring, voice) | `opencode` CLI subprocess, `opencode-go/deepseek-v4-pro` |
| AI (document generation, Fase 4) | Anthropic Python SDK, `claude-opus-4-8` — Agent Skills/`web_fetch` have no opencode equivalent |
| Document parsing | pdfplumber (+ hyperlink extraction), python-docx, odfpy, `pdftotext -layout` fallback |
| Data / sheet | pandas, openpyxl |
| Sheets sync | gspread + service account (not yet implemented) |
| Document generation | Claude Agent Skills (`docx`/`pdf`) via code execution container (Fase 4) |
| API / CLI | FastAPI + Typer |

See AGENTS.md Decision Log for why text-generation tasks use `opencode`/DeepSeek instead of the
Anthropic SDK directly (explicit user decision, confirmed mid-session).

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
- `feature/data-pipeline` (current): ingestion + analytics + knowledge base workbook (the MVP deliverable)
- `feature/voice-profile` (next): style guide extraction from cover letters
- `feature/generation-engine` (after): CV/cover-letter tailoring per job posting
- `feature/freelance-profiles` (after): assisted profile drafts per platform
- `feature/web-job-search` (future iteration): autonomous job search via web search / scheduled agents

---

## Current State

### Scaffold [COMPLETE]
**Branch**: `feature/initial-config`

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
- Section detection (`sections.py`) via ES/EN keyword matching on header lines (including a
  dedicated `links` section); language detection via header keywords with a stopword-ratio
  fallback for header-less prose (cover letters).
- **Hyperlink extraction**: all three formats expose real link targets (LinkedIn/GitHub/project
  URLs) separately from the text layer (PDF page annotations, DOCX/ODT relationship targets) -
  plain-text extraction alone only sees the anchor text ("LinkedIn", not the URL). Appended as a
  `Links:` block so PersonalData ends up with actual URLs, not link labels.
- **Result on the real corpus**: 48/48 source files ingested with zero crashes, 0 extraction
  warnings, 0 undetected languages. 37/38 CVs got full section coverage; 1 CV has no section
  headers at all in its source layout and correctly falls back to the `unstructured` bucket.
- Fixed two real bugs found during verification: (1) `pdfplumber(layout=True)` pads output with
  large whitespace runs that broke the alpha-ratio "garbled text" heuristic and the
  LibreOffice-as-txt-converter fallback (LibreOffice treats standalone PDFs as Draw documents and
  fails to save as text) — replaced with `pdftotext -layout` and a whitespace-aware ratio; (2)
  `layout=True` sometimes double-spaces header text ("Resumen  Profesional"), breaking substring
  keyword matching — fixed by collapsing whitespace runs before comparing.

### Data Analytics + Knowledge Base Workbook [COMPLETE — MVP DELIVERABLE SHIPPED]
**Branch**: `feature/data-pipeline`

- `analytics/dedupe.py`: mechanical (non-LLM) line-level dedup across all 38 CV versions before
  any LLM call — cut raw volume from ~281K to ~70K chars, and this is what makes each per-section
  LLM call small/fast/reliable.
- `analytics/structure.py`: one LLM call per canonical section (personal_data, summary,
  experience, education+certifications, skills, projects, languages) - translates to English,
  merges near-duplicate facts, extracts structured fields (company/role/dates for experience,
  category for skills, etc). Split per-section rather than one giant call - see Decision Log.
- `analytics/cover_letters.py`: translates all 10 cover letters to English, preserving the
  original text alongside (needed by the upcoming voice-style skill).
- `analytics/cv_versions.py`: deterministic inventory of all 38 CV files, grouped by stack
  (top-level folder), flagging the most-recently-modified file per stack.
- `analytics/checkpoint.py`: every LLM step's result is cached to `data/.checkpoints/` (gitignored)
  so `cvpal build-sheet` can be re-run in short bursts and resume instead of re-paying completed
  calls — necessary because the full pipeline exceeds the harness's ~10min background execution
  ceiling in one shot.
- `knowledge/workbook.py`: builds `data/cv-knowledge-base.xlsx` with all 11 tabs (PersonalData,
  Summary, Experience, Education, Certifications, Skills, Projects, Languages, CVVersions,
  CoverLetters, VoiceProfile-placeholder). **This file is committed to git** — per the Decision
  Log it's the source of truth, not a build artifact.
- **Result on the real corpus**: 12 personal data fields (incl. real LinkedIn/GitHub/project
  URLs — 2 different GitHub usernames and phone numbers found across CV history, both preserved
  as distinct facts, not silently merged), 5 summary variants, 43 experience bullets cleanly
  grouped by company/role/dates, 2 education entries, 3 certifications (including one recent one
  — a Sui blockchain bootcamp — not previously noticed), 113 skills categorized, 3 projects, 3
  languages, 38 CV versions tracked, 10 cover letters translated.
- Fixed a real bug during verification: uncapped `source_files` provenance lists blew up JSON
  output size for near-universal facts (e.g. "Java" appearing in 30+ of 38 files), truncating
  the LLM response mid-string. Capped at 3 representative files per record.
- 33 tests total (added `test_dedupe.py`, `test_checkpoint.py`, `test_cv_versions.py`,
  `test_workbook.py` — all pure/deterministic, no LLM calls in the automated suite). `ruff check`
  clean.
- **Not yet implemented**: Google Sheets sync (`cvpal sync` / `knowledge/sheets_sync.py`) - the
  `.xlsx` is the shipped deliverable; Sheets sync is the next small addition if needed.

### Not started
- Google Sheets sync (small addition to Fase 2, can be picked up anytime)
- Voice profile extraction (Fase 3) — **next up**
- Generation engine (Fase 4)
- Freelance profiles (Fase 5)
- Web job search (Fase 6, future)

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
python -u -m cvpal.cli ingest         # re-parse all source docs (fast, no LLM)
python -u -m cvpal.cli build-sheet    # structure + translate + build workbook (calls opencode/DeepSeek)
```

`build-sheet` may need to be re-run 2-3 times if killed by an external time limit - it resumes
from `data/.checkpoints/` automatically. Delete that directory to force a full recompute (e.g.
after changing a structuring prompt).

---

## Next Actions

1. Voice profile extraction (Fase 3): `src/cvpal/voice/style_guide.py` reading the `CoverLetters`
   tab, producing `data/voice-profile.md` + populating the `VoiceProfile` tab.
2. Optionally: Google Sheets sync before moving on, if Bruno wants to review/edit in Sheets now.
3. Generation engine (Fase 4) — first real use of the Anthropic SDK in this project (Agent
   Skills for `.docx`/`.pdf` output, `web_fetch` for the job posting URL).
