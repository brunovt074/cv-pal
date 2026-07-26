# Contributing to cv-pal

## Dev setup

```bash
git clone https://github.com/brunovt074/cv-pal.git
cd cv-pal
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # optional - see README.md for the config.toml path instead
```

LibreOffice (`soffice` on `PATH`) is needed to exercise PDF rendering locally; everything else
runs without external dependencies.

## Running checks

```bash
pytest                    # full test suite
ruff check src tests      # lint (rule set pinned in pyproject.toml - see [tool.ruff.lint])
```

Both must pass before opening a pull request.

## Branch and commit conventions

- Never commit directly to `main`
- Feature branches: `feature/descriptive-name`; fix branches: `fix/descriptive-name`
- Conventional commit prefixes: `feat:`, `fix:`, `test:`, `refactor:`, `chore:`

## Code conventions

See `AGENTS.md` for the full set of conventions this codebase follows (hexagonal architecture,
layering rules, testing expectations) - it's written for AI coding agents but applies equally to
human contributors, and is the single source of truth for both. `skills/*/SKILL.md` has deeper
guidance for specific areas (document extraction, voice/style, CV generation, the MCP server).

## Reporting issues

Open a GitHub issue with steps to reproduce. For anything touching personal-data handling, please
don't include real CV content, phone numbers, or emails in the report - use placeholder values.
