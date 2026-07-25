"""Bootstraps the knowledge base from ingested CV documents: one agent
call per canonical section, each returning JSON validated against a
domain model - not markdown text directly. A deterministic renderer
(infrastructure/persistence/markdown_knowledge_repository.py) turns the
validated KnowledgeBase into data/knowledge-base.md afterward, so this use
case is testable with a scripted FakeTextAgent and no real LLM call.

Each section is checkpointed by a fingerprint of its own deduped input
(see application/services/checkpointing.py) - a section whose underlying
CV content hasn't changed since the last run costs zero agent calls, and
only the sections actually affected by a corpus change are recomputed.
This makes it safe to call this use case defensively (e.g. before every
agent interaction) rather than only when a human remembers to.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, TypeVar

from pydantic import BaseModel

from cvpal.application.prompts import extraction, voice
from cvpal.application.services.checkpointing import (
    fingerprint_text,
    with_checkpoint_list,
    with_checkpoint_raw,
)
from cvpal.application.services.dedupe import DedupedBlock, dedupe_section_lines, fingerprint_blocks
from cvpal.application.services.personal_data_resolution import apply_known_corrections
from cvpal.application.services.response_parsing import complete_as
from cvpal.domain.documents.models import RawDocument
from cvpal.domain.knowledge.models import (
    CertificationEntry,
    EducationEntry,
    ExperienceBullet,
    KnowledgeBase,
    LanguageEntry,
    PersonalDataField,
    ProjectEntry,
    SkillEntry,
    SummaryEntry,
)
from cvpal.domain.knowledge.voice import VoiceProfile
from cvpal.domain.ports.checkpoint_store import CheckpointStorePort
from cvpal.domain.ports.text_completion import TextCompletionPort

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class KnowledgeBaseBuildReport:
    knowledge_base: KnowledgeBase
    rebuilt_sections: list[str] = field(default_factory=list)
    skipped_sections: list[str] = field(default_factory=list)


def _run_list_section(
    checkpoint_store: CheckpointStorePort,
    key: str,
    model_type: type[T],
    blocks: list[DedupedBlock],
    build_prompt: Callable[[list[DedupedBlock]], str],
    agent: TextCompletionPort,
    agent_name: str,
) -> tuple[list[T], bool]:
    fingerprint = f"{fingerprint_blocks(blocks)}:{extraction.PROMPT_VERSION}"

    def _compute() -> list[T]:
        if not blocks:
            return []
        return complete_as(agent, agent_name, build_prompt(blocks), list[model_type])

    return with_checkpoint_list(checkpoint_store, key, model_type, fingerprint, _compute)


def build_knowledge_base(
    documents: list[RawDocument],
    agent: TextCompletionPort,
    agent_name: str,
    checkpoint_store: CheckpointStorePort,
) -> KnowledgeBaseBuildReport:
    cvs = [d for d in documents if d.doc_kind == "cv"]
    rebuilt: list[str] = []
    skipped: list[str] = []

    def _track(key: str, was_recomputed: bool) -> None:
        (rebuilt if was_recomputed else skipped).append(key)

    personal_blocks = dedupe_section_lines(cvs, "header") + dedupe_section_lines(cvs, "links")
    personal_fingerprint = f"{fingerprint_blocks(personal_blocks)}:{extraction.PROMPT_VERSION}"

    def _compute_personal_data() -> list[PersonalDataField]:
        if not personal_blocks:
            return []
        raw = complete_as(
            agent, agent_name, extraction.personal_data_prompt(personal_blocks), list[PersonalDataField]
        )
        return apply_known_corrections(raw)

    personal_data, changed = with_checkpoint_list(
        checkpoint_store, "personal_data", PersonalDataField, personal_fingerprint, _compute_personal_data
    )
    _track("personal_data", changed)

    summaries, changed = _run_list_section(
        checkpoint_store,
        "summaries",
        SummaryEntry,
        dedupe_section_lines(cvs, "summary"),
        extraction.summary_prompt,
        agent,
        agent_name,
    )
    _track("summaries", changed)

    experience, changed = _run_list_section(
        checkpoint_store,
        "experience",
        ExperienceBullet,
        dedupe_section_lines(cvs, "experience"),
        extraction.experience_prompt,
        agent,
        agent_name,
    )
    _track("experience", changed)

    education_blocks = dedupe_section_lines(cvs, "education")
    education_fingerprint = f"{fingerprint_blocks(education_blocks)}:{extraction.PROMPT_VERSION}"

    def _compute_education_certifications() -> dict:
        if not education_blocks:
            return {"education": [], "certifications": []}
        return complete_as(
            agent, agent_name, extraction.education_and_certifications_prompt(education_blocks), dict
        )

    edu_certs_raw, changed = with_checkpoint_raw(
        checkpoint_store, "education_certifications", education_fingerprint, _compute_education_certifications
    )
    _track("education_certifications", changed)
    education = [EducationEntry.model_validate(e) for e in edu_certs_raw.get("education", [])]
    certifications = [
        CertificationEntry.model_validate(c) for c in edu_certs_raw.get("certifications", [])
    ]

    skills, changed = _run_list_section(
        checkpoint_store,
        "skills",
        SkillEntry,
        dedupe_section_lines(cvs, "skills"),
        extraction.skills_prompt,
        agent,
        agent_name,
    )
    _track("skills", changed)

    projects, changed = _run_list_section(
        checkpoint_store,
        "projects",
        ProjectEntry,
        dedupe_section_lines(cvs, "projects"),
        extraction.projects_prompt,
        agent,
        agent_name,
    )
    _track("projects", changed)

    languages, changed = _run_list_section(
        checkpoint_store,
        "languages",
        LanguageEntry,
        dedupe_section_lines(cvs, "languages"),
        extraction.languages_prompt,
        agent,
        agent_name,
    )
    _track("languages", changed)

    letters = [d for d in documents if d.doc_kind == "cover_letter" and d.unstructured]
    voice_input = "\n".join(
        f"{doc.source_file}:{doc.unstructured}" for doc in sorted(letters, key=lambda d: d.source_file)
    )
    voice_fingerprint = f"{fingerprint_text(voice_input)}:{voice.PROMPT_VERSION}"

    def _compute_voice_profile() -> dict | None:
        if not letters:
            return None
        return complete_as(agent, agent_name, voice.voice_profile_prompt(letters), dict)

    voice_raw, changed = with_checkpoint_raw(
        checkpoint_store, "voice_profile", voice_fingerprint, _compute_voice_profile
    )
    _track("voice_profile", changed)
    voice_profile = VoiceProfile.model_validate(voice_raw) if voice_raw else None

    knowledge_base = KnowledgeBase(
        personal_data=personal_data,
        summaries=summaries,
        experience=experience,
        education=education,
        certifications=certifications,
        skills=skills,
        projects=projects,
        languages=languages,
        voice_profile=voice_profile,
    )
    return KnowledgeBaseBuildReport(
        knowledge_base=knowledge_base, rebuilt_sections=rebuilt, skipped_sections=skipped
    )
