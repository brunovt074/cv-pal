# Skill: qa-code

## Scope

Whole repository — code quality audits, refactors, and pre-merge checks.

## When to read this skill

Before running a broad refactor, before a code-review pass, before merging a feature branch.

## Checklist

- `ruff check src tests` clean.
- `pytest` green; no skipped tests without a tracked reason.
- No hand-rolled logic duplicating a library already in `pyproject.toml` (e.g. don't hand-roll
  fuzzy string matching if `rapidfuzz`/similar is already a dependency — check before adding a
  new one too).
- Every pydantic model crossing a module boundary (ingest → analytics → knowledge → agents) is
  actually typed — no bare `dict[str, Any]` smuggled through as "the CV record".
- No secrets (`ANTHROPIC_API_KEY`, Google service-account JSON) committed — check `.gitignore`
  coverage before every commit that touches `.env*` or credential-shaped filenames.
- Knowledge-base-schema changes are reflected in `skills/data-analytics/SKILL.md` and any
  downstream reader (`voice-style`, `cv-generation`) in the same change — a schema drift here is
  a silent breakage, not a compile error.
