# Skill: data-analytics

## Scope

`src/cvpal/analytics/` and `src/cvpal/knowledge/` — turning the raw `RawDocument` records from
ingestion into the deduplicated, normalized, English-language knowledge base workbook
(`data/cv-knowledge-base.xlsx`) and its Google Sheets mirror. This is the module that produces
the MVP deliverable — treat schema changes here as high-stakes.

## When to read this skill

Before changing dedupe logic, the translation step, or any tab/column in the workbook schema.

## Principles

- **English is the standard language of the knowledge base — always.** Every textual field
  (summaries, experience bullets, project descriptions) is normalized to English before it is
  written to any tab, regardless of the source document's language. This is a hard rule, not a
  default that varies by row. Translation to Spanish (or any other language) happens only later,
  at CV-generation time (`cv-generation` skill), never stored as a second copy in the base.
  - Use `claude-opus-4-8` for translation of any block longer than a few words; don't
    hand-roll translation heuristics.
  - Every row keeps `source_language` in its trace metadata so a human can audit the translation
    against the original if something reads oddly.
- **Deduplication across CV versions is the core analytics problem.** The same role
  ("Desarrollador de Software Java – Reyesoft") appears, worded slightly differently, across
  multiple files in `Java/`, `cv-latests/`, `generic/`. Treat records as duplicates when
  `(company, role, start_date)` match closely (fuzzy match on company/role strings — Levenshtein
  or similar, not exact match) — then merge by keeping the **union of distinct bullets** across
  versions (bullets that say the same thing in different words are still duplicates — dedupe
  those too) and preferring the **most recent file's phrasing** when bullets conflict.
- **Traceability metadata on every row:** `source_file`, `source_language`, `confidence`
  (how sure the merge/translation logic is), `last_seen` (most recent source file's mtime).
- **The workbook schema is the contract other modules build on** (`cv-generation` reads it,
  `voice-style` reads the CoverLetters tab). Any schema change is a breaking change — update
  `AGENTS.md`'s Decision Log and any downstream reader in the same change.

## Workbook schema (tabs)

`PersonalData`, `Summary`, `Experience` (one row per bullet, not per role — so tailoring can
pick individual bullets), `Education`, `Certifications`, `Skills`, `Projects`, `Languages`,
`CVVersions` (inventory of all source docs), `CoverLetters` (inventory + normalized text),
`VoiceProfile` (populated by the `voice-style` skill, not this one).

## Google Sheets sync

`knowledge/sheets_sync.py` pushes the same tabs via `gspread` using a service-account credential
(`GOOGLE_SERVICE_ACCOUNT_FILE` env var — never commit this file; it's in `.gitignore`). The sync
is one-directional (xlsx → Sheets) for the MVP — Sheets is for human review, not concurrent
editing. If Bruno edits the Sheet directly, that edit is not pulled back automatically; flag this
limitation in the CLI output after `cvpal sync`.

## Testing

- Unit-test the dedupe/fuzzy-match logic with small synthetic `RawDocument` fixtures covering:
  exact duplicate, near-duplicate wording, genuinely different roles that share a company name.
- Unit-test translation only for the *plumbing* (does the field get replaced, is
  `source_language` preserved) — do not assert on exact translated wording, that's an LLM
  integration test, not a unit test, and belongs behind a `--live` pytest marker that hits the
  real API.
