from cvpal.domain.knowledge.models import (
    ExperienceBullet,
    KnowledgeBase,
    PersonalDataField,
    SkillEntry,
)
from cvpal.domain.knowledge.voice import VoiceProfile
from cvpal.infrastructure.persistence.markdown_knowledge_repository import (
    MarkdownKnowledgeRepository,
)


def _sample_kb() -> KnowledgeBase:
    return KnowledgeBase(
        personal_data=[
            PersonalDataField(field="name", value="Bruno Vargas Tettamanti", source_files=["a.pdf"]),
            PersonalDataField(field="phone", value="+5493772566242 (current)", source_files=["a.pdf", "b.pdf"]),
        ],
        experience=[
            ExperienceBullet(
                company="Acme",
                role="Developer",
                start_date="01/2020",
                end_date="Present",
                modality="Remote",
                bullet="Built REST APIs | with pipes",
                tech_tags=["Java", "Spring"],
                source_files=["a.pdf"],
            )
        ],
        skills=[SkillEntry(skill="Java", category="language", source_files=["a.pdf", "b.pdf", "c.pdf"])],
        voice_profile=VoiceProfile(
            opening_style="Direct",
            recurring_phrases=["I am excited to", "hands-on experience"],
            tone_summary=["direct", "technical"],
        ),
        notes="Some free-form human note.\n\nWith a blank line.",
    )


def test_save_creates_file(tmp_path):
    path = tmp_path / "kb.md"
    repo = MarkdownKnowledgeRepository(path)
    repo.save(_sample_kb())
    assert path.exists()
    assert "# Bruno Vargas Tettamanti" in path.read_text()


def test_roundtrip_preserves_all_sections(tmp_path):
    path = tmp_path / "kb.md"
    repo = MarkdownKnowledgeRepository(path)
    original = _sample_kb()
    repo.save(original)

    loaded = repo.load()

    assert loaded.personal_data[0].field == "name"
    assert loaded.personal_data[0].value == "Bruno Vargas Tettamanti"
    assert loaded.personal_data[1].value == "+5493772566242 (current)"
    assert set(loaded.personal_data[1].source_files) == {"a.pdf", "b.pdf"}

    assert loaded.experience[0].company == "Acme"
    assert loaded.experience[0].bullet == "Built REST APIs | with pipes"
    assert loaded.experience[0].tech_tags == ["Java", "Spring"]

    assert loaded.skills[0].skill == "Java"
    assert len(loaded.skills[0].source_files) == 3

    assert loaded.voice_profile is not None
    assert loaded.voice_profile.opening_style == "Direct"
    assert loaded.voice_profile.recurring_phrases == ["I am excited to", "hands-on experience"]
    assert loaded.voice_profile.tone_summary == ["direct", "technical"]

    assert "Some free-form human note." in loaded.notes


def test_load_tolerates_a_manually_added_row(tmp_path):
    path = tmp_path / "kb.md"
    repo = MarkdownKnowledgeRepository(path)
    repo.save(_sample_kb())

    text = path.read_text()
    text = text.replace(
        "| Java | language |  |  |  | a.pdf, b.pdf, c.pdf |",
        "| Java | language |  |  |  | a.pdf, b.pdf, c.pdf |\n"
        "| Kotlin | language | Ssr | 2 | manually added | notes.md |",
    )
    path.write_text(text)

    loaded = repo.load()
    skills_by_name = {s.skill: s for s in loaded.skills}
    assert "Kotlin" in skills_by_name
    assert skills_by_name["Kotlin"].seniority == "Ssr"


def test_load_returns_empty_lists_for_untouched_missing_file_sections(tmp_path):
    path = tmp_path / "kb.md"
    path.write_text("# Empty\n\n<!-- cvpal:section=personal_data -->\n## Personal Data\n\n_(none)_\n<!-- /cvpal:section -->\n")
    repo = MarkdownKnowledgeRepository(path)
    loaded = repo.load()
    assert loaded.personal_data == []
    assert loaded.experience == []
    assert loaded.voice_profile is None


def test_exists_reflects_filesystem(tmp_path):
    path = tmp_path / "kb.md"
    repo = MarkdownKnowledgeRepository(path)
    assert repo.exists() is False
    repo.save(_sample_kb())
    assert repo.exists() is True
