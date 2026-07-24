from cvpal.application.services.personal_data_resolution import apply_known_corrections
from cvpal.domain.knowledge.models import PersonalDataField


def test_preferred_phone_tagged_current():
    fields = [PersonalDataField(field="phone", value="+5493772566242")]
    resolved = apply_known_corrections(fields)
    assert resolved[0].value == "+5493772566242 (current)"


def test_older_phone_variants_tagged_previous():
    fields = [
        PersonalDataField(field="phone", value="+5492604101707"),
        PersonalDataField(field="phone", value="+542604101707"),
        PersonalDataField(field="phone", value="+543772566242"),
    ]
    resolved = apply_known_corrections(fields)
    assert all(v.value.endswith("(previous)") for v in resolved)


def test_preferred_linkedin_tagged_current_and_others_previous():
    fields = [
        PersonalDataField(field="linkedin", value="https://www.linkedin.com/in/bruno-vargas-tettamanti-dev/"),
        PersonalDataField(
            field="linkedin", value="https://www.linkedin.com/in/bruno-vargas-tettamanti-developer/"
        ),
        PersonalDataField(field="linkedin", value="https://www.linkedin.com/in/brunodev-pdl/"),
    ]
    resolved = apply_known_corrections(fields)
    assert resolved[0].value.endswith("(current)")
    assert resolved[1].value.endswith("(previous)")
    assert resolved[2].value.endswith("(previous)")


def test_preferred_github_tagged_current():
    fields = [
        PersonalDataField(field="github", value="brunovt074"),
        PersonalDataField(field="github", value="brunovargas-pdl"),
    ]
    resolved = apply_known_corrections(fields)
    assert resolved[0].value.endswith("(current)")
    assert resolved[1].value.endswith("(previous)")


def test_fields_without_a_known_preference_pass_through_unchanged():
    fields = [PersonalDataField(field="email", value="brunodev.pdl@gmail.com")]
    resolved = apply_known_corrections(fields)
    assert resolved[0].value == "brunodev.pdl@gmail.com"
