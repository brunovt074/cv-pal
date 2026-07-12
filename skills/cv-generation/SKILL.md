# Skill: cv-generation

## Scope

`src/cvpal/agents/cv_tailor.py`, `src/cvpal/agents/cover_letter.py`, `src/cvpal/llm/` — the core
of historia 2: given a job posting URL, produce a tailored CV and cover letter as real
`.docx`/`.pdf` files, written in Bruno's voice, in the right language.

## When to read this skill

Before writing or modifying any tailoring prompt, before wiring Agent Skills / server tools for
document generation, before changing how the knowledge base or voice profile are loaded into
context.

## Principles

- **Fetch the posting with `web_fetch_20260209`.** Declare it as a server tool on the request;
  don't scrape client-side. The tool only fetches URLs already present in the conversation, so
  the job URL must be in the user turn.
- **Load the knowledge base as stable context, cache it.** The workbook content (or the relevant
  slice: Experience, Skills, Education, Summary, VoiceProfile) is the same across every tailoring
  request in a session — put it in `system` with `cache_control: {"type": "ephemeral"}` so
  repeated runs in the same session are cheap. See `shared/prompt-caching.md` in the claude-api
  skill for placement rules if this needs tuning later.
- **Selection before writing.** The tailoring step is fundamentally: (1) read the job posting,
  (2) select the subset of Experience bullets / Skills / Projects that are actually relevant —
  do not dump the entire history into every CV, that's not "tailored" — (3) write the CV and
  cover letter using only the selected material, in the extracted voice.
- **Language detection and on-the-fly translation.** Default output language is inferred from the
  job posting (if it's in Spanish, the CV/letter should be in Spanish; English posting → English
  output) unless the user explicitly overrides it. This is where the "translate on the fly"
  decision from the Decision Log gets executed — the knowledge base stays English, the
  *generation* step is what translates, using the language-independent traits from the voice
  profile (see `voice-style` skill) so tone survives translation.
- **Real files, not just text.** Use Agent Skills (`docx`, `pdf`) via the `container` parameter +
  `code_execution_20260521` tool, with both betas `code-execution-2025-08-25` and
  `skills-2025-10-02` on `client.beta.messages.create`. Output lands as a file in the response;
  download it via the Files API and save to `data/outputs/`. Do not settle for returning markdown
  text as the "CV" — Bruno needs a document he can actually submit.
- **Never fabricate experience.** The model must only use material present in the knowledge
  base. If the job posting calls for something not in Bruno's background, the tailored CV should
  honestly omit it or frame adjacent real experience — never invent a skill, certification, or
  project. State this constraint explicitly and firmly in the system prompt.

## Output

Two files per run in `data/outputs/`, named predictably (e.g.
`{company}-{role}-{date}.{cv,cover-letter}.docx`), plus the `.pdf` if requested.

## Testing

- Unit-test selection logic (given a mock job posting + mock knowledge base, does it pick
  plausible bullets) separately from generation (which needs a live API call).
- End-to-end verification is manual for the MVP: run against a real posting, open the resulting
  document, check content accuracy and voice — see the `verify` skill's general guidance on
  driving real behavior instead of only asserting on code structure.
