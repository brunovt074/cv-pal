"""Bootstraps the knowledge base from ingested CV documents: one agent
call per canonical section, each returning JSON validated against a
domain model - not markdown text directly. A deterministic renderer
(infrastructure/persistence/markdown_knowledge_repository.py) turns the
validated KnowledgeBase into data/knowledge-base.md afterward, so this use
case is testable with a scripted FakeTextAgent and no real LLM call.

Each step is checkpointed so a killed/interrupted run resumes instead of
re-paying completed calls - see skills/data-analytics/SKILL.md.
"""

from __future__ import annotations

from cvpal.application.prompts import extraction, voice
from cvpal.application.services.checkpointing import with_checkpoint_list, with_checkpoint_raw
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
from cvpal.application.services.dedupe import dedupe_section_lines


def build_knowledge_base(
    documents: list[RawDocument],
    agent: TextCompletionPort,
    agent_name: str,
    checkpoint_store: CheckpointStorePort,
) -> KnowledgeBase:
    cvs = [d for d in documents if d.doc_kind == "cv"]

    def _personal_data() -> list[PersonalDataField]:
        blocks = dedupe_section_lines(cvs, "header") + dedupe_section_lines(cvs, "links")
        if not blocks:
            return []
        raw = complete_as(
            agent, agent_name, extraction.personal_data_prompt(blocks), list[PersonalDataField]
        )
        return apply_known_corrections(raw)

    def _summaries() -> list[SummaryEntry]:
        blocks = dedupe_section_lines(cvs, "summary")
        if not blocks:
            return []
        return complete_as(agent, agent_name, extraction.summary_prompt(blocks), list[SummaryEntry])

    def _experience() -> list[ExperienceBullet]:
        blocks = dedupe_section_lines(cvs, "experience")
        if not blocks:
            return []
        return complete_as(
            agent, agent_name, extraction.experience_prompt(blocks), list[ExperienceBullet]
        )

    def _education_certifications() -> dict:
        blocks = dedupe_section_lines(cvs, "education")
        if not blocks:
            return {"education": [], "certifications": []}
        return complete_as(
            agent, agent_name, extraction.education_and_certifications_prompt(blocks), dict
        )

    def _skills() -> list[SkillEntry]:
        blocks = dedupe_section_lines(cvs, "skills")
        if not blocks:
            return []
        return complete_as(agent, agent_name, extraction.skills_prompt(blocks), list[SkillEntry])

    def _projects() -> list[ProjectEntry]:
        blocks = dedupe_section_lines(cvs, "projects")
        if not blocks:
            return []
        return complete_as(agent, agent_name, extraction.projects_prompt(blocks), list[ProjectEntry])

    def _languages() -> list[LanguageEntry]:
        blocks = dedupe_section_lines(cvs, "languages")
        if not blocks:
            return []
        return complete_as(agent, agent_name, extraction.languages_prompt(blocks), list[LanguageEntry])

    def _voice_profile() -> dict | None:
        letters = [d for d in documents if d.doc_kind == "cover_letter" and d.unstructured]
        if not letters:
            return None
        return complete_as(agent, agent_name, voice.voice_profile_prompt(letters), dict)

    personal_data = with_checkpoint_list(
        checkpoint_store, "personal_data", PersonalDataField, _personal_data
    )
    summaries = with_checkpoint_list(checkpoint_store, "summaries", SummaryEntry, _summaries)
    experience = with_checkpoint_list(checkpoint_store, "experience", ExperienceBullet, _experience)

    edu_certs_raw = with_checkpoint_raw(
        checkpoint_store, "education_certifications", _education_certifications
    )
    education = [EducationEntry.model_validate(e) for e in edu_certs_raw.get("education", [])]
    certifications = [
        CertificationEntry.model_validate(c) for c in edu_certs_raw.get("certifications", [])
    ]

    skills = with_checkpoint_list(checkpoint_store, "skills", SkillEntry, _skills)
    projects = with_checkpoint_list(checkpoint_store, "projects", ProjectEntry, _projects)
    languages = with_checkpoint_list(checkpoint_store, "languages", LanguageEntry, _languages)

    voice_raw = with_checkpoint_raw(checkpoint_store, "voice_profile", _voice_profile)
    voice_profile = VoiceProfile.model_validate(voice_raw) if voice_raw else None

    return KnowledgeBase(
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
