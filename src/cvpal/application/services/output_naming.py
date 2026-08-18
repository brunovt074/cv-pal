"""Build the conventional output path for a tailored CV or cover letter.

Convention:
    {user-slug}-cv-{company-lowercase-slug}.{ext}              for CVs
    cover-letter/{user-slug}-cl-{company-lowercase-slug}.{ext}  for cover letters

Cover letters ALWAYS live under a `cover-letter/` subfolder of the outputs
directory - keeps CVs and cover letters for the same application easy to
spot together, and stops the outputs root from mixing the two
interchangeably. The return value is a relative path, so callers do
`outputs_dir / build_output_path(...)` and the renderer creates the
subfolder on demand (see `infrastructure/rendering/local_document_renderer.py`).

`{user-slug}` identifies the author and is per-user - never hardcoded,
always passed in by the caller (`domain.user.profile.UserProfile.slug`,
see PROJECT_STATUS for the naming convention's why).

The company name is normalized to a filesystem-safe slug: lowercased,
whitespace and `.`/`,` collapsed to `-`, accents stripped, anything that
isn't [a-z0-9-] removed. A blank or fully-stripped company name falls
back to `untitled` so the file is still valid (and obviously tells the
user to supply a real company name next time).
"""

from __future__ import annotations

import re
import unicodedata

_KIND_PREFIX = {"cv": "cv", "cover_letter": "cl"}
_KIND_SUBDIR = {"cv": "", "cover_letter": "cover-letter"}
_FALLBACK_COMPANY = "untitled"

_NON_SLUG_CHARS = re.compile(r"[^a-z0-9-]+")
_MULTI_HYPHEN = re.compile(r"-+")
_DIACRITIC_FOLDS = str.maketrans(
    {
        "ø": "o",
        "Ø": "o",
        "æ": "ae",
        "Æ": "ae",
        "œ": "oe",
        "Œ": "oe",
        "ß": "ss",
        "đ": "d",
        "Đ": "d",
        "ł": "l",
        "Ł": "l",
    }
)


def _slugify_company(company: str) -> str:
    folded = company.translate(_DIACRITIC_FOLDS)
    normalized = unicodedata.normalize("NFKD", folded.strip())
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    lower = ascii_only.lower()
    hyphenated = re.sub(r"[\s._,]+", "-", lower)
    stripped = _NON_SLUG_CHARS.sub("", hyphenated)
    collapsed = _MULTI_HYPHEN.sub("-", stripped).strip("-")
    return collapsed or _FALLBACK_COMPANY


def build_output_path(*, kind: str, company: str, extension: str, user_slug: str) -> str:
    if kind not in _KIND_PREFIX:
        raise ValueError(f"Unknown document kind: {kind!r}. Use 'cv' or 'cover_letter'.")
    prefix = _KIND_PREFIX[kind]
    slug = _slugify_company(company)
    leaf = f"{user_slug}-{prefix}-{slug}.{extension}"
    subdir = _KIND_SUBDIR[kind]
    if not subdir:
        return leaf
    return f"{subdir}/{leaf}"
