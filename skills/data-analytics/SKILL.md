# Skill: data-analytics

## Scope

`src/cvpal/application/use_cases/build_knowledge_base.py`, `application/prompts/extraction.py`,
`application/prompts/voice.py`, `application/services/dedupe.py`,
`application/services/personal_data_resolution.py`, and
`infrastructure/persistence/markdown_knowledge_repository.py` — turning the raw `RawDocument`
records from ingestion into `data/knowledge-base.md`, the single source of truth for all
downstream agents. Treat schema changes to `domain/knowledge/models.py` as high-stakes: they
change both the markdown table shape and any downstream reader (`cv-generation`).

## When to read this skill

Before changing dedupe logic, an extraction prompt, the personal-data correction rules, or the
markdown knowledge base's table shape.

## Principles

- **The markdown file is the contract, not the agent's raw text.** Each extraction prompt
  (`application/prompts/extraction.py`) asks the configured agent for JSON matching a
  `domain/knowledge/models.py` pydantic model, validated via
  `application/services/response_parsing.complete_as` — never for markdown prose directly. A
  deterministic renderer (`markdown_knowledge_repository.save()`) turns the validated
  `KnowledgeBase` into `data/knowledge-base.md` afterward. This keeps `build_knowledge_base()`
  testable with a scripted `FakeTextAgent` (see `tests/fakes/fake_text_agent.py`) instead of
  needing a live LLM call in the test suite.
- **English is the standard language of the knowledge base — always.** Every textual field is
  normalized to English before it's written to any section, regardless of source document
  language — this is a hard rule stated in every extraction prompt's `_COMMON_RULES`, not a
  default that varies by row. Translation to Spanish (or any other language) happens only later,
  at CV-tailoring time (`cv-generation` skill), never stored as a second copy.
- **Mechanical dedup before any agent call.** `application/services/dedupe.py` collapses
  near-identical lines across all ~38 CV versions before the extraction prompt ever sees them —
  this is what keeps each per-section call small, fast, and reliable. It is pure/deterministic
  (no I/O, no agent) and lives in `application/`, not `infrastructure/`, for exactly that reason.
- **One agent call per canonical section**, checkpointed independently
  (`application/services/checkpointing.py` + `infrastructure/persistence/file_checkpoint_store.py`).
  A single call covering everything triggers unreliable behavior (see `infrastructure/agents/`
  docstrings on tool-permission denial for large outputs in non-interactive CLI agents) — keep
  each call's *output* small.
- **Which value is "current" is a fact, never an agent guess.** When the same personal-data field
  (phone, LinkedIn, GitHub) has multiple distinct values across ~50 CV variants spanning years,
  the extraction prompt returns ALL distinct values — `application/services/personal_data_resolution.py`
  then deterministically tags exactly one as `(current)` against a hardcoded authoritative value,
  and the rest `(previous)`. Never ask an agent to pick; it has no way to know which is right.
- **Traceability, not a full audit trail.** Every record's `source_files` is capped at 3
  representative files even if a fact appears in 30+ — enough to spot-check, not to enumerate
  every duplicate (uncapped lists blow up JSON output size for near-universal facts and truncate
  the response mid-string).

## Knowledge base sections

`Personal Data`, `Summary` (2-3 variants by focus area), `Experience` (one row per bullet, not
per role — so tailoring can pick individual bullets), `Education`, `Certifications`, `Skills`,
`Projects`, `Languages`, `Voice Profile` (see `voice-style` skill — extracted in the same
`build_knowledge_base()` pass from cover letters, not a separate step), and a free-form `Notes`
section a human can add to by hand — preserved verbatim across `cvpal kb build` reruns (unlike
the structured sections, which regenerate from scratch).

## Rebuilding vs. editing

`cvpal kb build` re-runs every extraction call and overwrites the structured sections — only run
it when new CVs are added to the source corpus. Between rebuilds, `data/knowledge-base.md` is
meant to be hand-edited directly (fix a row, adjust a skill's seniority, correct a translation) —
the markdown table format was chosen specifically so both a human and any future agent converge
on the same file through the same shape.

## Testing

- Unit-test `dedupe.py` with small synthetic `RawDocument` fixtures: exact duplicate,
  near-duplicate wording, genuinely different lines.
- Unit-test `personal_data_resolution.py` against the corpus's actual known-inconsistent values
  (see `tests/application/test_personal_data_resolution.py`) — this is the one place a
  substring-matching bug silently mis-tags data (e.g. "-dev" matching inside "-developer"), so
  keep exact-match assertions, not just "doesn't crash".
- Unit-test `build_knowledge_base()` end-to-end with a `FakeTextAgent` scripted with realistic
  JSON responses (see `tests/application/test_build_knowledge_base.py`) — no live agent call in
  the automated suite.
- Unit-test `markdown_knowledge_repository.py`'s save→load roundtrip, including a hand-edited
  file (added row, extra whitespace) to confirm the parser tolerates manual edits.
