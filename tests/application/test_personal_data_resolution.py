from cvpal.application.services.personal_data_resolution import apply_known_corrections
from cvpal.domain.knowledge.models import PersonalDataField

_PREFERRED = {
    "phone": "+1-555-0100",
    "linkedin": "https://www.linkedin.com/in/alex-doe-dev/",
    "github": "alexdoe",
}


def test_preferred_phone_tagged_current():
    fields = [PersonalDataField(field="phone", value="+1-555-0100")]
    resolved = apply_known_corrections(fields, _PREFERRED)
    assert resolved[0].value == "+1-555-0100 (current)"


def test_older_phone_variants_tagged_previous():
    fields = [
        PersonalDataField(field="phone", value="+1-555-0199"),
        PersonalDataField(field="phone", value="+1-555-0200"),
        PersonalDataField(field="phone", value="+1-555-0300"),
    ]
    resolved = apply_known_corrections(fields, _PREFERRED)
    assert all(v.value.endswith("(previous)") for v in resolved)


def test_preferred_linkedin_tagged_current_and_others_previous():
    fields = [
        PersonalDataField(field="linkedin", value="https://www.linkedin.com/in/alex-doe-dev/"),
        PersonalDataField(field="linkedin", value="https://www.linkedin.com/in/alex-doe-developer/"),
        PersonalDataField(field="linkedin", value="https://www.linkedin.com/in/alexdoe-old/"),
    ]
    resolved = apply_known_corrections(fields, _PREFERRED)
    assert resolved[0].value.endswith("(current)")
    assert resolved[1].value.endswith("(previous)")
    assert resolved[2].value.endswith("(previous)")


def test_preferred_github_tagged_current():
    fields = [
        PersonalDataField(field="github", value="alexdoe"),
        PersonalDataField(field="github", value="alex-doe-old"),
    ]
    resolved = apply_known_corrections(fields, _PREFERRED)
    assert resolved[0].value.endswith("(current)")
    assert resolved[1].value.endswith("(previous)")


def test_fields_without_a_known_preference_pass_through_unchanged():
    fields = [PersonalDataField(field="email", value="alex.doe@example.com")]
    resolved = apply_known_corrections(fields, _PREFERRED)
    assert resolved[0].value == "alex.doe@example.com"
