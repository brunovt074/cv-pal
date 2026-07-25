from cvpal.application.services.agent_view import render_agent_view
from cvpal.domain.knowledge.models import (
    ExperienceBullet,
    KnowledgeBase,
    PersonalDataField,
    SkillEntry,
)
from cvpal.domain.knowledge.voice import VoiceProfile


def _kb_with_variants() -> KnowledgeBase:
    return KnowledgeBase(
        personal_data=[
            PersonalDataField(field="phone", value="+5493772566242 (current)", source_files=["a.pdf", "b.pdf"]),
            PersonalDataField(field="phone", value="+5492604101707 (previous)", source_files=["c.pdf"]),
            PersonalDataField(field="email", value="brunodev.pdl@gmail.com", source_files=["a.pdf"]),
        ],
        experience=[
            ExperienceBullet(
                company="Acme",
                role="Developer",
                start_date="01/2020",
                end_date="Present",
                bullet="Built REST APIs",
                tech_tags=["Java"],
                source_files=["a.pdf", "b.pdf", "c.pdf"],
            )
        ],
        skills=[
            SkillEntry(skill="Java", category="language", seniority="Sr", source_files=["a.pdf", "b.pdf"]),
            SkillEntry(skill="Docker", category="tool", source_files=["a.pdf"]),
        ],
    )


def test_agent_view_drops_previous_personal_data_variants():
    view = render_agent_view(_kb_with_variants())
    assert "+5493772566242" in view
    assert "+5492604101707" not in view
    assert "(previous)" not in view
    assert "(current)" not in view  # marker itself is stripped once resolved


def test_agent_view_drops_source_files_everywhere():
    view = render_agent_view(_kb_with_variants())
    assert "a.pdf" not in view
    assert "b.pdf" not in view
    assert "c.pdf" not in view


def test_agent_view_keeps_experience_and_skills_content():
    view = render_agent_view(_kb_with_variants())
    assert "Acme" in view
    assert "Built REST APIs" in view
    assert "Java" in view
    assert "Docker" in view


def test_agent_view_reports_missing_voice_profile():
    view = render_agent_view(_kb_with_variants())
    assert "not yet extracted" in view


def test_agent_view_includes_voice_profile_when_present():
    kb = _kb_with_variants().model_copy(
        update={"voice_profile": VoiceProfile(opening_style="Direct", tone_summary=["direct", "technical"])}
    )
    view = render_agent_view(kb)
    assert "Direct" in view
    assert "direct, technical" in view


def test_agent_view_is_meaningfully_smaller_than_full_markdown(tmp_path):
    from cvpal.infrastructure.persistence.markdown_knowledge_repository import (
        MarkdownKnowledgeRepository,
    )

    kb = _kb_with_variants()
    path = tmp_path / "kb.md"
    MarkdownKnowledgeRepository(path).save(kb)
    full_text = path.read_text()

    lean_text = render_agent_view(kb)
    assert len(lean_text) < len(full_text)
