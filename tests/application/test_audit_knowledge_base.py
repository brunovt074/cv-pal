from cvpal.application.use_cases.audit_knowledge_base import audit_personal_data
from cvpal.domain.knowledge.models import KnowledgeBase, PersonalDataField


def test_audit_reports_fields_with_multiple_values():
    kb = KnowledgeBase(
        personal_data=[
            PersonalDataField(field="phone", value="+1-555-0100 (current)"),
            PersonalDataField(field="phone", value="+1-555-0199 (previous)"),
            PersonalDataField(field="email", value="alex.doe@example.com"),
        ]
    )
    inconsistencies = audit_personal_data(kb)
    assert len(inconsistencies) == 1
    assert inconsistencies[0].field == "phone"
    assert len(inconsistencies[0].values) == 2


def test_audit_returns_empty_when_all_fields_are_unique():
    kb = KnowledgeBase(
        personal_data=[
            PersonalDataField(field="email", value="alex.doe@example.com"),
            PersonalDataField(field="name", value="Alex Doe"),
        ]
    )
    assert audit_personal_data(kb) == []
