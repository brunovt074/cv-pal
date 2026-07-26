# Skill: voice-style

## Scope

`src/cvpal/domain/knowledge/voice.py` (the `VoiceProfile` model),
`src/cvpal/application/prompts/voice.py` (the extraction prompt) — extracting a reusable "how the
author writes" style guide from their existing cover letters, so tailored CVs and cover letters
sound like the author instead of generic AI output. This is not a separate pipeline step — it runs
inside `application/use_cases/build_knowledge_base.py`, in the same pass as everything else, and
lands in the `Voice Profile` section of `data/knowledge-base.md`.

## When to read this skill

Before touching `application/prompts/voice.py`, before writing any prompt in `cv-generation` that
claims to "respect the user's voice", and before changing `VoiceProfile`'s shape.

## Principles

- **Source of truth is the existing cover letters** (`RawDocument` records with
  `doc_kind="cover_letter"`, ingested alongside the CVs). Do not ask the author to write a new sample
  for the MVP — analyze what already exists first; only fall back to asking for a fresh writing
  sample if the existing letters are too sparse/inconsistent to extract a confident profile.
- **Extract structure, not just adjectives.** A useful voice profile answers concrete questions
  an LLM prompt can act on:
  - Typical opening move (does the author lead with enthusiasm for the role, a concrete
    achievement, a connection to the company?)
  - Sentence length and rhythm (short punchy sentences vs. longer compound ones)
  - First-person framing (how much "I" vs. describing accomplishments passively)
  - Recurring phrases or framings the author reuses across letters (these are load-bearing —
    they're what makes output recognizably theirs)
  - What the author explicitly avoids (buzzwords, over-claiming, generic enthusiasm)
  - Closing style
- **Output is the `Voice Profile` section of `data/knowledge-base.md`** — human-readable (a
  Trait/Value table the author can review/correct directly) and machine-readable (parsed back into
  `VoiceProfile` by `markdown_knowledge_repository.load()` for `cv-generation` prompts) from the
  same file. No separate `voice-profile.md` or spreadsheet tab.
- **Language-aware.** `language_specific_traits` should note whether the observed patterns hold
  in both English and Spanish source letters, or if there's a notable difference in register
  between them (common — people write more formally in a second/professional language). If the
  author isn't a native English speaker, `cv-generation` needs to reflect their actual proficiency
  level without pretending native fluency, not smooth it over.
- **Re-extraction is cheap — treat the profile as regenerable, not hand-authored.** If new cover
  letters are added to the source corpus, re-running `cvpal kb build` is the expected workflow.
  Manual corrections to the Voice Profile table survive as long as the row shape (Trait/Value)
  is kept; anything that doesn't fit that shape belongs in the knowledge base's `Notes` section,
  which is preserved verbatim across rebuilds.

## Testing

- Since this is fundamentally a qualitative LLM task, testing is: (1) the plumbing
  (`build_knowledge_base()` with a `FakeTextAgent`, does it produce a `VoiceProfile`; the
  markdown roundtrip, does save→load preserve every field) as unit tests, and (2) a manual
  verification step — generate a paragraph using the profile and confirm it sounds like the author.
  Don't try to unit-test "does this sound like the author" programmatically.
