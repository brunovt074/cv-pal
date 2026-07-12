# Skill: data-extraction

## Scope

`src/cvpal/ingest/` — turning raw CV/cover-letter files (PDF, DOCX, ODT) into normalized,
structured pydantic records. This is the first stage of the pipeline; nothing downstream should
ever touch a raw file directly.

## When to read this skill

Before creating or modifying any extractor, parser, or section-detection logic under `ingest/`.

## Principles

- **One extractor per file format**, dispatched by extension: `pdf_extractor.py`,
  `docx_extractor.py`, `odt_extractor.py`. Each returns the same intermediate representation
  (raw text + layout hints), not a parsed CV — parsing is a separate step.
- **Layout-tolerant parsing.** These documents were written by hand over years in different tools
  (LibreOffice, Word, Google Docs exports) — section headers, bullet styles, and date formats are
  inconsistent. Section detectors must work off heading keywords (`Experience`, `Experiencia`,
  `Educación`, `Habilidades Técnicas`, etc. — see the ES/EN keyword list in `sections.py`) rather
  than assuming fixed positions.
- **Fallback chain for PDFs:** try `pdfplumber` with `layout=True` first; if the extracted text is
  empty or clearly garbled (e.g. < 20% alphabetic characters), fall back to
  `soffice --headless --convert-to txt` (already installed on this machine) and re-parse.
- **Never lose provenance.** Every extracted record carries `source_file` (path relative to the
  CV root) and `source_language` (best-effort detection — heuristic keyword match on section
  headers is enough; do not spin up an LLM call per file just for this).
- **Fail loud, not silent.** If a file cannot be parsed into any recognizable section, still emit
  a record with the raw text under an `unstructured` field and log a warning — never drop a
  source file silently. Bruno needs to know which files did not extract cleanly.

## Output contract

Every extractor returns a `RawDocument` (pydantic model) with:
- `source_file: str`
- `source_language: str` (`"es"` | `"en"` | `"unknown"`)
- `sections: dict[str, str]` — best-effort section name → raw text blob
- `unstructured: str | None` — fallback bucket when section detection fails

Parsing `sections` into typed records (Experience, Education, Skills, …) happens in
`analytics/`, not here — keep ingestion dumb and mechanical, keep interpretation in analytics
where it can be tested against the full corpus at once.

## Testing

- Fixture-based: drop 2-3 representative real files per format under `tests/fixtures/` (already
  covers the range: a clean recent PDF, an older messier one, a DOCX, an ODT) and assert
  `sections` contains the expected keys, not exact text (exact text is brittle across
  LibreOffice/pdfplumber version bumps).
- No test should assert on more than the presence/absence of expected section keys and rough
  content length — over-specifying breaks on tool version changes.
