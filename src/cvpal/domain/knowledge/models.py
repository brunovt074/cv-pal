from __future__ import annotations

from pydantic import BaseModel, Field

from cvpal.domain.knowledge.voice import VoiceProfile


class PersonalDataField(BaseModel):
    field: str
    value: str
    source_files: list[str] = Field(default_factory=list)


class SummaryEntry(BaseModel):
    variant_label: str
    text: str
    source_files: list[str] = Field(default_factory=list)


class ExperienceBullet(BaseModel):
    company: str
    role: str
    start_date: str
    end_date: str
    modality: str = ""
    location: str = ""
    bullet: str
    tech_tags: list[str] = Field(default_factory=list)
    source_files: list[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    institution: str
    program: str
    program_type: str = ""
    date: str = ""
    status: str = ""
    source_files: list[str] = Field(default_factory=list)


class CertificationEntry(BaseModel):
    name: str
    issuer: str = ""
    date: str = ""
    source_files: list[str] = Field(default_factory=list)


class SkillEntry(BaseModel):
    skill: str
    category: str = ""
    seniority: str = ""
    years: str = ""
    evidence: str = ""
    source_files: list[str] = Field(default_factory=list)


class ProjectEntry(BaseModel):
    name: str
    description: str
    tech: list[str] = Field(default_factory=list)
    role: str = ""
    source_files: list[str] = Field(default_factory=list)


class LanguageEntry(BaseModel):
    language: str
    level: str = ""
    source_files: list[str] = Field(default_factory=list)


class KnowledgeBase(BaseModel):
    """The single, versioned source of truth for all CV content.

    Rendered to/parsed from `data/knowledge-base.md` by
    `infrastructure.persistence.markdown_knowledge_repository`.
    """

    personal_data: list[PersonalDataField] = Field(default_factory=list)
    summaries: list[SummaryEntry] = Field(default_factory=list)
    experience: list[ExperienceBullet] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    certifications: list[CertificationEntry] = Field(default_factory=list)
    skills: list[SkillEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    languages: list[LanguageEntry] = Field(default_factory=list)
    voice_profile: VoiceProfile | None = None
    notes: str = Field(
        default="",
        description=(
            "Free-form markdown a human can add by hand - preserved verbatim "
            "across `kb build` regenerations, unlike the structured sections above."
        ),
    )
