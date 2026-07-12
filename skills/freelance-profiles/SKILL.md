# Skill: freelance-profiles

## Scope

`src/cvpal/agents/profile_builder.py` — historia 3: generating draft profile content (headline,
bio, skills list, suggested rates, portfolio blurb) for freelance platforms, for Bruno to paste
and review manually.

## When to read this skill

Before adding a new platform, before changing what fields a profile draft includes, before
considering any form of automated account creation or posting.

## Hard constraint: human-in-the-loop only, by design

This was an explicit user decision, not a technical shortcut — **do not automate account
creation, form-filling, or posting on Upwork or Fiverr.** Both platforms' Terms of Service
prohibit account automation, and there is no public API for profile creation on either. Browser
automation against these platforms risks account bans. The agent's job stops at generating
well-crafted **content**; Bruno performs the actual paste/submit action himself.

- If a platform *does* expose a real API for this purpose (evaluate case-by-case — e.g. some
  job boards, potentially Himalayas), API-driven publishing is fine and preferred over manual
  paste. Confirm the API is official and ToS-compliant before wiring it, and note the exception
  in this file when you do.
- Never suggest or implement scraping, headless-browser form submission, or credential storage
  for Upwork/Fiverr login as a way to "fully automate" this — that request should be redirected
  back to the content-generation approach.

## Principles

- **One generator function per platform**, not one generic template — each platform has a
  distinct format and constraints (character limits, required fields, tone expectations: Upwork
  is more formal/corporate, Fiverr leans punchier/service-oriented, Superprof is
  teaching-focused, Himalayas is remote-work focused). Read the platform's actual profile
  structure before writing its generator.
- **Draw from the same knowledge base and voice profile as `cv-generation`** — don't re-derive
  Bruno's background or tone independently. A freelance profile is still Bruno's voice, adapted
  to a different format and audience, not a different persona.
- **Output as markdown per platform** in `data/outputs/profiles/{platform}.md`, structured so
  each field Bruno needs to paste is clearly labeled (Headline:, Bio:, Skills:, ...) — optimize
  for "easy to copy one field at a time into a web form", not for prose readability.

## Testing

- Verification is manual: generate the four platform drafts, have Bruno read and confirm before
  he pastes anything live. No automated test can validate "does this read well on Upwork" —
  don't try.
