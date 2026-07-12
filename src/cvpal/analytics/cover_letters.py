"""Builds the CoverLetters tab: inventory of cover letters plus an
English translation of each, kept alongside the original.

The original text is preserved (not just the translation) because
skills/voice-style/SKILL.md needs to compare voice traits across languages -
translating away the source text would lose that signal.
"""

from __future__ import annotations

import json
from pathlib import Path

from cvpal.analytics.models import CoverLetterEntry
from cvpal.ingest.models import RawDocument
from cvpal.llm.opencode_client import call_opencode_json

_PROMPT_TEMPLATE = """\
Translate each of the following cover letters to English, preserving tone, \
structure, and personal voice as closely as possible - this is not a \
formal/literal translation, it should read like the author naturally wrote \
it in English. Letters already in English should be returned unchanged.

Output ONLY a single JSON array (no markdown fences, no prose), one object \
per letter, in the same order as given, with this exact shape:
[{{"source_file": str, "english_text": str}}]

Letters:
{letters_block}
"""


def _format_letters(documents: list[RawDocument]) -> str:
    parts = []
    for doc in documents:
        parts.append(f"--- {doc.source_file} ---\n{doc.unstructured or ''}")
    return "\n\n".join(parts)


def _translate(letters: list[RawDocument]) -> dict[str, str]:
    prompt = _PROMPT_TEMPLATE.format(letters_block=_format_letters(letters))
    raw = call_opencode_json(prompt)
    return {item["source_file"]: item["english_text"] for item in raw}


def build_cover_letters(
    documents: list[RawDocument], checkpoint_dir: Path | None = None
) -> list[CoverLetterEntry]:
    letters = [d for d in documents if d.doc_kind == "cover_letter" and d.unstructured]
    if not letters:
        return []

    if checkpoint_dir is None:
        translations = _translate(letters)
    else:
        checkpoint_path = checkpoint_dir / "cover_letter_translations.json"
        if checkpoint_path.exists():
            translations = json.loads(checkpoint_path.read_text())
        else:
            translations = _translate(letters)
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            checkpoint_path.write_text(json.dumps(translations, indent=2, ensure_ascii=False))

    entries = []
    for doc in letters:
        entries.append(
            CoverLetterEntry(
                source_file=doc.source_file,
                source_language=doc.source_language,
                original_text=doc.unstructured or "",
                english_text=translations.get(doc.source_file, doc.unstructured or ""),
            )
        )
    return entries
