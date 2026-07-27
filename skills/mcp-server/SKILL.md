# Skill: mcp-server

## Scope

`src/cvpal/interfaces/mcp/server.py` — cv-pal's primary interface: an MCP server over stdio that
any MCP-capable agent (opencode, Claude Code) consumes as a tool, the same way this project
already consumes engram. `cvpal serve-mcp` starts it.

## When to read this skill

Before adding/changing an MCP tool or prompt, before touching the `cv_pal` prompt's protocol text,
before changing which use case backs a handler.

## Principles

- **The host agent writes, cv-pal provides.** This is the central design decision (see AGENTS.md
  Decision Log). cv-pal never runs a nested LLM call to draft a CV or cover letter - the `cv_pal`
  prompt hands the host's own model a lean knowledge base view + the posting + a protocol, and the
  host drafts and prints the result in its own conversation. The only tool that calls the
  configured backend agent (`CVPAL_AGENT`) is `rebuild_knowledge_base`.
- **One-shot over orchestration.** `/cv-pal` is a single prompt call, not a sequence of granular
  fetches the host has to assemble itself - that would cost more round-trips and tokens for no
  quality gain, since the host still ends up needing the same material either way. Granular tools
  (`get_cv_material`, `get_knowledge_base`) exist for inspection/editing, not as the default path.
- **Thin handlers, real logic in `application/`.** Every `@mcp.tool()`/`@mcp.prompt()` function is
  a one-liner: build a `Container`, call a `_verb(container, ...)` function, return text. The
  `_verb` functions are what's actually tested (`tests/interfaces/test_mcp_server.py`) - they take
  the `Container` as a plain argument so tests never touch the MCP protocol, env vars, or a real
  process. Keep new tools in this shape; don't grow logic inside the decorated function.
- **No extra parameters on decorated functions.** Whatever a `@mcp.tool()`/`@mcp.prompt()`
  function accepts becomes part of the schema an agent sees. Don't add a `container` parameter (or
  anything else) to the public-facing function to make it "more testable" - that leaks
  implementation detail into the tool's contract. Testability comes from the `_verb` split above.
- **Interfaces never import infrastructure directly.** `interfaces/mcp/server.py` only imports
  `application` + `domain` + `container` - like `interfaces/cli/`. Verify with
  `grep -rln "cvpal.infrastructure" src/cvpal/interfaces/mcp` (must be empty).
- **A missing knowledge base is a guided message, not a crash.** Every handler that needs
  `data/knowledge-base.md` checks `container.knowledge_repository.exists()` first and returns
  `_onboarding_message(container)` instead of raising - a tri-state guide (never configured / no
  CV source files yet / configured with files but not ingested) rather than one flat message, so
  the host agent always has a concrete next action regardless of how far along the user is.

## Tool/prompt contract

| Name | Kind | Calls an agent? | Purpose |
|------|------|:---:|---------|
| `cv_pal` | prompt | no | Assembles the one-shot tailoring prompt (lean KB view + posting + protocol). Primary entry point |
| `configure` | tool | no | First-run and ongoing setup - writes `~/.config/cvpal/config.toml` (raw CV directory, default output language, name/slug). Called by the host agent conversationally, not just from `cvpal init` in a terminal |
| `get_cv_material` | tool | no | Lean agent view as markdown, standalone |
| `get_knowledge_base` | tool | no | Full markdown (with provenance), whole doc or one section |
| `update_knowledge_base` | tool | no | Host-initiated edit; validates against a near-total-wipe heuristic, backs up, writes |
| `audit_knowledge_base` | tool | no | Personal-data fields with multiple distinct values |
| `ingest_corpus` | tool | no | Re-scan `CV_RAW_DIR`, skipping unchanged files |
| `rebuild_knowledge_base` | tool | **yes** (`CVPAL_AGENT`) | Regenerate the KB; zero agent calls if nothing changed (content-addressed checkpointing, see `data-analytics` skill) - safe to call defensively |
| `render_document` | tool | no | Markdown → real `.docx`/`.pdf` via `infrastructure/rendering/` |

## Client configuration

Both configs point at the same thing: `cvpal-mcp` (equivalently, `cvpal serve-mcp`) over stdio.
Installed from PyPI, `uvx` resolves the binary with no local checkout needed - see README.md.
Working from a local clone instead, use the venv's full binary path (`.venv/bin/cvpal-mcp`).

**opencode** (`~/.config/opencode/opencode.jsonc`, alongside engram):

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

## Testing

- Every handler's `_verb(container, ...)` function is tested directly against a `Container` built
  from a `Settings` pointed at `tmp_path` (see `tests/interfaces/test_mcp_server.py`) - no real MCP
  process, no env vars. For `rebuild_knowledge_base`, inject a `FakeTextAgent` by setting
  `container._agent` directly before calling.
- After changing the tool surface, sanity-check registration once with the real SDK:
  ```python
  import asyncio
  from cvpal.interfaces.mcp.server import mcp
  asyncio.run(mcp.list_tools())   # and mcp.list_prompts()
  ```
- End-to-end verification is manual and required before calling a change to this file done: start
  `cvpal serve-mcp` from opencode **and** Claude Code with the config above, confirm the tools
  appear, and drive `/cv-pal` with a real job posting against the real knowledge base.
