from cvpal.application.services.output_naming import build_output_path

_SLUG = "alex-doe"


def test_build_output_path_cv_lowercases_company_and_slugifies():
    assert (
        build_output_path(kind="cv", company="Proxify", extension="pdf", user_slug=_SLUG)
        == "alex-doe-cv-proxify.pdf"
    )


def test_build_output_path_cover_letter_uses_cl_prefix_and_cover_letter_subfolder():
    assert (
        build_output_path(kind="cover_letter", company="Proxify", extension="docx", user_slug=_SLUG)
        == "cover-letter/alex-doe-cl-proxify.docx"
    )


def test_build_output_path_replaces_whitespace_with_hyphen():
    assert (
        build_output_path(kind="cv", company="Acme Corp", extension="pdf", user_slug=_SLUG)
        == "alex-doe-cv-acme-corp.pdf"
    )


def test_build_output_path_strips_accents():
    assert (
        build_output_path(kind="cv", company="Müller & Søn", extension="pdf", user_slug=_SLUG)
        == "alex-doe-cv-muller-son.pdf"
    )


def test_build_output_path_keeps_alphanumeric_and_hyphens():
    assert (
        build_output_path(kind="cv", company="Acme.io", extension="md", user_slug=_SLUG)
        == "alex-doe-cv-acme-io.md"
    )


def test_build_output_path_falls_back_to_untitled_when_company_blank():
    assert (
        build_output_path(kind="cv", company="", extension="pdf", user_slug=_SLUG)
        == "alex-doe-cv-untitled.pdf"
    )
    assert (
        build_output_path(kind="cv", company="   ", extension="pdf", user_slug=_SLUG)
        == "alex-doe-cv-untitled.pdf"
    )
    assert (
        build_output_path(kind="cv", company="!!!", extension="pdf", user_slug=_SLUG)
        == "alex-doe-cv-untitled.pdf"
    )


def test_build_output_path_cover_letter_falls_back_to_untitled_inside_subfolder():
    assert (
        build_output_path(kind="cover_letter", company="", extension="pdf", user_slug=_SLUG)
        == "cover-letter/alex-doe-cl-untitled.pdf"
    )


def test_build_output_path_rejects_unknown_kind():
    import pytest

    with pytest.raises(ValueError, match="Unknown document kind"):
        build_output_path(kind="resume", company="X", extension="pdf", user_slug=_SLUG)
