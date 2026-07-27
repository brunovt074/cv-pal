# Skill: skill-creator

## Scope

Creating and evolving project-specific skills under `skills/`.

## When to read this skill

Before adding a new `skills/{name}/SKILL.md`, or when an existing skill needs restructuring.

## Rules

- One skill per concern area matching a `src/cvpal/` module (see the table in `AGENTS.md`), not
  per task or per file.
- Every new skill must be registered in `AGENTS.md`'s Skills table and Auto-invoke Rules table in
  the same change.
- A `SKILL.md` should state: scope, when to read it, principles (the non-obvious constraints —
  not a tutorial on the library being used), and testing approach. Keep it prescriptive, not a
  restatement of what the code already makes obvious.
