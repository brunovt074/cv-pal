# Skill: voice-style

## Scope

`src/cvpal/voice/` — extracting a reusable "how Bruno writes" style guide from his existing
cover letters, so generated CVs and cover letters sound like him instead of like generic AI
output.

## When to read this skill

Before touching `voice/style_guide.py`, before writing any prompt in `cv-generation` that claims
to "respect the user's voice", and before regenerating `data/voice-profile.md`.

## Principles

- **Source of truth is the existing cover letters**, inventoried in the `CoverLetters` tab of the
  knowledge base (populated by `data-analytics`). Do not ask Bruno to write a new sample for the
  MVP — analyze what already exists first; only fall back to asking for a fresh writing sample if
  the existing letters are too sparse/inconsistent to extract a confident profile.
- **Extract structure, not just adjectives.** A useful voice profile answers concrete questions
  an LLM prompt can act on:
  - Typical opening move (does he lead with enthusiasm for the role, a concrete achievement, a
    connection to the company?)
  - Sentence length and rhythm (short punchy sentences vs. longer compound ones)
  - First-person framing (how much "I" vs. describing accomplishments passively)
  - Recurring phrases or framings he reuses across letters (these are load-bearing — they're
    what makes output recognizably his)
  - What he explicitly avoids (buzzwords, over-claiming, generic enthusiasm)
  - Closing style
- **Output is dual: machine and human-readable.**
  - `data/voice-profile.md` — human-readable, so Bruno can review/correct it directly (he said
    he wants voice-guide accuracy — give him an editable artifact, not a black box).
  - `VoiceProfile` tab in the workbook — same content, structured, so `cv-generation` prompts can
    pull it programmatically without parsing markdown.
- **Language-aware.** The voice profile should note whether the observed patterns hold in both
  English and Spanish source letters, or if there's a notable difference in register between
  them (common — people write more formally in a second/professional language). This matters
  because Fase 4 translates on-the-fly and needs to know which voice traits are
  language-independent (structure, directness) vs. language-specific (idioms, formality markers).
- **Re-extraction is cheap — treat the profile as regenerable, not hand-authored.** If Bruno adds
  new cover letters to the source corpus later, re-running `cvpal voice` should be the expected
  workflow, not a one-time manual edit. Keep any manual corrections Bruno makes in
  `voice-profile.md` clearly marked so a regeneration doesn't silently overwrite them (e.g. a
  `<!-- manual overrides below, preserved on regeneration -->` section).

## Testing

- Since this is fundamentally a qualitative LLM task, testing is: (1) the plumbing (does it read
  CoverLetters, does it write both outputs) as a unit test with fixture data, and (2) a manual
  verification step — generate a paragraph using the profile and have Bruno confirm it sounds
  like him. Don't try to unit-test "does this sound like Bruno" programmatically.
