# CV-Pal

Agent-agnostic CV/cover-letter tailoring, consumed as an MCP server over stdio by your AI
agent — opencode, Claude Code, or anything else that speaks MCP — the same way you'd already
consume something like engram: you ask your agent to use cv-pal, it reads your real knowledge
base and drafts the CV/cover letter itself, conversing with you. A secondary CLI (`cvpal ...`)
also exists for a non-conversational, single-shot path. Hexagonal architecture throughout: the
agent that builds the knowledge base is swappable via one environment variable — `opencode` today,
anything else tomorrow — without touching business logic. See `AGENTS.md` for the full layer
breakdown.

## What it does

1. **Ingestion** — parses PDF/DOCX/ODT documents from your configured CV source directory,
   skipping files that haven't changed since the last run.
2. **Knowledge base** — mechanical dedupe + one agent call per section (personal data, summary,
   experience, education, certifications, skills, projects, languages, voice profile), validated
   against typed models and rendered to a single markdown file — the source of truth. Every
   section is checkpointed by content fingerprint, so re-running costs nothing when nothing
   changed.
3. **MCP server** (`cvpal-mcp` / `cvpal serve-mcp`) — your agent asks for a lean view of the
   knowledge base (no provenance metadata, roughly 44% of the full size) plus the job posting, and
   drafts the CV itself, then conversationally the cover letter — asking about tone if it hasn't
   captured your voice yet, confirming it if it has. cv-pal never makes a nested LLM call for
   this; only `rebuild_knowledge_base` calls the configured agent.
4. **Document rendering** — real `.docx`/`.pdf` files generated locally (`python-docx` +
   LibreOffice), no agent or API key needed.
5. **CLI** (`cvpal tailor`) — secondary, non-conversational path, same result in one step.

## Requirements

- Python 3.12+
- [LibreOffice](https://www.libreoffice.org/) installed and on `PATH` (`soffice` binary) — only
  needed for PDF output; markdown/docx work without it
- One of the supported CLI agents installed and authenticated — `opencode` or `claude` (Claude
  Code) — **only for `cvpal kb build` / `rebuild_knowledge_base`** (the one-time step that turns
  your raw CVs into the knowledge base). Everything downstream of that (tailoring, rendering) uses
  no agent and no API key. If you're driving cv-pal from Claude Desktop or another host with no
  CLI agent installed, you'll need to install `opencode` or Claude Code separately just for this
  step - there's no built-in fallback yet.

## Quickstart

```bash
pip install cv-pal
cvpal init      # interactive: your name, output-filename slug, CV source directory, agent
cvpal doctor    # verifies everything is wired up correctly
```

Then point your agent at the MCP server (see below), or drive it from the CLI:

```bash
cvpal ingest
cvpal kb build
cvpal tailor --job-text "Backend Java, Spring Boot, remote" --format pdf
```

## Connect to your agent (primary path)

**opencode** (`~/.config/opencode/opencode.jsonc`):

```jsonc
{
  "mcp": {
    "cvpal": {
      "command": ["uvx", "--from", "cv-pal", "cvpal-mcp"],
      "enabled": true,
      "type": "local"
    }
  }
}
```

**Claude Code**:

```bash
claude mcp add cvpal -- uvx --from cv-pal cvpal-mcp
```

Once connected, ask your agent to use cv-pal to tailor your CV to a job posting. See
`skills/mcp-server/SKILL.md` for the full tool/prompt contract.

## CLI reference (secondary path)

```bash
cvpal ingest                 # parse CV_RAW_DIR into normalized JSON
cvpal kb build                # (re)build the knowledge base via the configured agent
cvpal kb audit                # report personal-data fields with conflicting values
cvpal tailor --job-text "..." --format pdf
cvpal tailor --job-file posting.docx --language es --format docx
cvpal clean --all             # wipe generated outputs
cvpal agents list / check     # inspect the configured text-completion agent
cvpal doctor                  # environment diagnostics
cvpal init                    # (re)run the setup wizard
```

## Configuration

`cvpal init` writes `~/.config/cvpal/config.toml`; environment variables (including a plain
`.env` file, see `.env.example`) override it. Your knowledge base and generated outputs live under
`~/.local/share/cvpal/` by default.

## Documentation

- `AGENTS.md` — conventions for AI agents working in this codebase, hexagonal architecture
  (single source of truth for contributors)
- `PROJECT_STATUS.md` — current implementation state and branch history
- `skills/` — focused guides per area (extraction, voice, generation, MCP server)
- `CONTRIBUTING.md` — dev setup, running tests/lint, branch and commit conventions

## License

MIT — see `LICENSE`.
