# Skill: cv-generation

## Scope

`src/cvpal/application/use_cases/tailor_cv.py`, `application/prompts/tailoring.py`,
`infrastructure/job_postings/`, `infrastructure/agents/` — given a job posting (text, file, or
URL), produce a CV tailored to it from `data/knowledge-base.md`, written in the author's voice,
in the right language. Currently markdown-out only; real `.docx`/`.pdf` output and a cover
letter use case are the natural next steps (see Not Yet Wired below).

## When to read this skill

Before writing or modifying the tailoring prompt, before wiring a `DocumentRenderPort` or
`WebContentPort` adapter, before changing how the knowledge base is loaded into context.

## Principles

- **The knowledge base markdown IS the context — pass it whole, not a parsed slice.** Any agent
  (opencode today, anything else tomorrow) reads `data/knowledge-base.md` as-is; there's no
  provider-specific structured-context mechanism to keep portable across agents. If context size
  becomes a problem, trim in `tailor_cv.py` before building the prompt, not by changing the file
  format.
- **Selection happens inside the prompt, not as a separate pre-filter.** The tailoring prompt
  (`application/prompts/tailoring.py:tailor_cv_prompt`) explicitly instructs the agent to select
  only the Experience bullets / Skills / Projects relevant to the posting — dumping the entire
  history into every CV is not "tailored". If output quality suffers, the next step is a
  deterministic pre-filter use case ahead of the prompt, not a bigger prompt.
- **Language detection and on-the-fly translation.** Output language is inferred from the job
  posting text (`infrastructure/parsers/sections.py:detect_language`, injected into `tailor_cv()`
  as a callable — see the dependency-injection note in `container.py`) unless overridden via
  `--language`. The knowledge base stays English; translation happens only at generation time,
  guided by the language-independent voice traits (see `voice-style` skill) so tone survives
  translation.
- **Never fabricate experience.** The prompt states firmly: use ONLY material in the knowledge
  base; if the posting calls for something absent, honestly omit it or frame the closest real,
  adjacent experience — never invent a skill, certification, or project.

## Not yet wired (by design, not oversight)

- **Real `.docx`/`.pdf` output** needs a `DocumentRenderPort` adapter
  (`domain/ports/document_render.py`) — no adapter implements it yet. `tailor_cv()` currently
  returns markdown; `cvpal tailor` writes it straight to `data/outputs/*.md`.
- **Fetching a job posting URL** needs a `WebContentPort` adapter
  (`domain/ports/web_content.py`). `infrastructure/job_postings/url_source.py` raises
  `CapabilityNotSupportedError` until one is registered. Note this is **not** a hard capability
  gap in opencode itself — it has a native `webfetch` tool and MCP support — the actual blocker is
  that its non-interactive `run` mode auto-denies tool permissions with no one to approve them
  (`opencode run --auto` may lift this; not exercised yet). Don't assume opencode categorically
  can't do this when deciding how to wire the adapter.
- **A cover-letter use case**, mirroring `tailor_cv.py`, hasn't been built — only CV generation
  has, matching what was actually asked for. Add `tailor_cover_letter.py` alongside it following
  the same pattern (prompt in `application/prompts/`, use case in `application/use_cases/`) when
  needed, rather than growing `tailor_cv.py` to do both.

## Output

`cvpal tailor --job-text "..."` / `--job-file posting.docx` writes `data/outputs/cv-tailored-{lang}.md`
(or a path given via `--output`).

## Testing

- Unit-test `tailor_cv()` with a `FakeTextAgent` and a fake `JobPostingSourcePort` (see
  `tests/application/test_tailor_cv.py`) — asserts the prompt contains both the posting and the
  knowledge base, and that language detection/override resolve correctly. No live agent call in
  the automated suite.
- End-to-end verification is manual: run `cvpal tailor` against a real posting, read the
  resulting markdown, check content accuracy and voice — see the `verify` skill's general
  guidance on driving real behavior instead of only asserting on code structure.
