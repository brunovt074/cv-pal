from cvpal.application.use_cases.update_knowledge_base import update_knowledge_base
from cvpal.domain.knowledge.models import ExperienceBullet, KnowledgeBase, SkillEntry


def _kb_with_records(n_skills: int) -> KnowledgeBase:
    return KnowledgeBase(
        experience=[
            ExperienceBullet(
                company="Acme", role="Dev", start_date="2020", end_date="Present", bullet="Did a thing"
            )
        ],
        skills=[SkillEntry(skill=f"skill-{i}") for i in range(n_skills)],
    )


def test_accepts_a_normal_edit():
    current = _kb_with_records(10)

    def fake_parse(_text: str) -> KnowledgeBase:
        return _kb_with_records(11)  # added one skill

    result = update_knowledge_base(current, "new markdown", fake_parse)
    assert result.accepted is True
    assert result.knowledge_base is not None
    assert len(result.knowledge_base.skills) == 11


def test_rejects_a_near_total_wipe():
    current = _kb_with_records(10)

    def fake_parse(_text: str) -> KnowledgeBase:
        return KnowledgeBase()  # empty

    result = update_knowledge_base(current, "garbage", fake_parse)
    assert result.accepted is False
    assert "force=True" in result.reason
    assert result.knowledge_base is None


def test_force_overrides_the_wipe_rejection():
    current = _kb_with_records(10)

    def fake_parse(_text: str) -> KnowledgeBase:
        return KnowledgeBase()

    result = update_knowledge_base(current, "garbage", fake_parse, force=True)
    assert result.accepted is True
    assert result.knowledge_base == KnowledgeBase()


def test_accepts_when_current_is_already_empty():
    current = KnowledgeBase()

    def fake_parse(_text: str) -> KnowledgeBase:
        return _kb_with_records(1)

    result = update_knowledge_base(current, "first content ever", fake_parse)
    assert result.accepted is True
