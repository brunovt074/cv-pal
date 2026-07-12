from __future__ import annotations

from pydantic import BaseModel, Field


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


class StructuredKnowledgeBase(BaseModel):
    personal_data: list[PersonalDataField] = Field(default_factory=list)
    summaries: list[SummaryEntry] = Field(default_factory=list)
    experience: list[ExperienceBullet] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    certifications: list[CertificationEntry] = Field(default_factory=list)
    skills: list[SkillEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    languages: list[LanguageEntry] = Field(default_factory=list)


class CVVersionEntry(BaseModel):
    source_file: str
    stack: str
    source_language: str
    is_most_recent_variant: bool = False


class CoverLetterEntry(BaseModel):
    source_file: str
    source_language: str
    original_text: str
    english_text: str
