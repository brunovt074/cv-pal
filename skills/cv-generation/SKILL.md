# Skill: cv-generation

## Scope

Two paths to the same outcome - a CV (and cover letter) tailored to a job posting from
`data/knowledge-base.md`, written in the author's voice, in the right language, using ONLY
material in the knowledge base:

- **CLI path** (`cvpal tailor`): `application/use_cases/tailor_cv.py`,
  `application/prompts/tailoring.py` - cv-pal itself calls the configured agent and writes a
  file.
- **MCP path** (primary - see `mcp-server` skill): `application/prompts/cv_pal.py` - cv-pal
  assembles a prompt, the *host* agent drafts and prints the CV/cover letter conversationally.
  No LLM call happens inside cv-pal for this path.

Both draw from the same job posting sources (`infrastructure/job_postings/`) and document
rendering (`infrastructure/rendering/`).

## When to read this skill

Before writing or modifying either tailoring prompt, before touching `infrastructure/rendering/`
or `infrastructure/web_content/` (the `WebContentPort` adapter), before changing how the knowledge
base is loaded into context.

## Principles

- **Selection happens inside the prompt, not as a separate pre-filter.** Both prompts explicitly
  instruct the agent to select only the Experience bullets / Skills / Projects relevant to the
  posting — dumping the entire history into every CV is not "tailored". If output quality suffers,
  the next step is a deterministic pre-filter use case ahead of the prompt, not a bigger prompt.
- **The MCP path uses the lean agent view, not the full markdown.** `cv_pal_prompt()` is built
  from `application/services/agent_view.py`'s output, not `data/knowledge-base.md` directly - see
  the `mcp-server` skill and `data-analytics` skill for why (provenance/superseded-variant
  stripping, token cost). The CLI path (`tailor_cv.py`) still passes the full markdown as-is,
  since it's a single cv-pal-side agent call, not a host-side conversation - the same
  optimization could be applied there later if it matters.
- **Output language defaults to English, on-the-fly translation only on request.** `tailor_cv()`
  and `_cv_pal()` resolve `language_override or "en"` — the job posting's language is never used to
  pick the output language. Only an explicit `--language`/`language` argument (CLI) or the user
  asking mid-conversation (MCP) changes it. The knowledge base stays English; translation happens
  only at generation time, guided by the language-independent voice traits (see `voice-style`
  skill) so tone survives translation. `infrastructure/parsers/sections.py:detect_language` still
  exists but is only used during ingestion to tag source documents' language, not for this.
- **Never fabricate experience.** Both prompts state firmly: use ONLY material in the knowledge
  base; if the posting calls for something absent, honestly omit it or frame the closest real,
  adjacent experience — never invent a skill, certification, or project.
- **Cover letters are conversational, not fire-and-forget.** The `cv_pal` MCP prompt instructs the
  host to ask before drafting a cover letter, then branch: if a voice profile exists, confirm the
  captured essence in a sentence or two before writing; if not, elicit tone/an example
  opener/what-to-highlight first. See `application/prompts/cv_pal.py:_voice_branch` and the
  `voice-style` skill. The CLI path has no cover-letter command - it's CV-only, matching what was
  actually asked for there; a `tailor_cover_letter.py` use case (mirroring `tailor_cv.py`) is the
  natural next step if a non-interactive cover-letter path is ever needed, but the interactive MCP
  path is what real usage should go through.
- **Document rendering needs no agent.** `infrastructure/rendering/local_document_renderer.py`
  converts markdown to `.docx` directly with `python-docx`, and to `.pdf` via a temp `.docx` +
  `soffice --headless --convert-to pdf`. Both the CLI (`cvpal tailor --format docx|pdf`) and the
  MCP `render_document` tool go through `container.document_renderer`. It only covers the markdown
  shape the tailoring prompts actually produce (headings, bold, bullets, paragraphs) - not a
  general-purpose renderer.
- **Fetching a job posting by URL needs no agent either.** `infrastructure/web_content/
  http_web_content.py` (`HttpWebContent`) implements `WebContentPort` (`domain/ports/
  web_content.py`) as a plain `urllib` fetch + stdlib `html.parser` tag-stripping — same
  local/deterministic reasoning as document rendering above, not an agent capability. Wired via
  `container.web_content` into `UrlJobPostingSource`; reachable from `cvpal tailor --job-url` (CLI)
  and the MCP `cv_pal` prompt's `job_posting_url` argument. `JobPostingFetchError` surfaces
  network/empty-page failures as a message, not a stack trace. This was previously blocked on
  opencode's non-interactive `run` mode auto-denying its native `webfetch` tool's permissions — a
  local adapter sidesteps that entirely, the same way `DOCUMENT_RENDER` bypassed agent-capability
  negotiation.

## Output

- CLI: `cvpal tailor --job-text "..." --format pdf` (or `--job-file posting.docx`, `--job-url
  https://...`, `docx`, `markdown`) writes `data/outputs/cv-tailored-{lang}.{ext}` (or a path via
  `--output`).
- MCP: the host prints the CV/cover letter in its own conversation; `render_document` converts
  whatever the host wrote into a real file under `data/outputs/` on request.

## Testing

- Unit-test `tailor_cv()` with a `FakeTextAgent` and a fake `JobPostingSourcePort` (see
  `tests/application/test_tailor_cv.py`); unit-test `cv_pal_prompt()` directly (see
  `tests/application/test_cv_pal_prompt.py`) — asserts posting/material/voice-branch presence. No
  live agent call in the automated suite for either.
- Unit-test `LocalDocumentRenderer` (see `tests/infrastructure/test_local_document_renderer.py`) —
  `.docx` opened back with `python-docx` and asserted on headings/bullets/bold/hyperlinks/font;
  `.pdf` skipped if `soffice` isn't installed, otherwise asserted to start with `%PDF` and be
  non-empty.
- Unit-test `HttpWebContent` (see `tests/infrastructure/test_web_content.py`) with
  `urllib.request.urlopen` mocked — no real network call in the automated suite.
- End-to-end verification is manual: run `cvpal tailor` against a real posting, or drive the
  `cv_pal` MCP prompt from opencode/Claude Code and read the result — see the `verify` skill's
  general guidance on driving real behavior instead of only asserting on code structure.
