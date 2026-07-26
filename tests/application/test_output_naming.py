from cvpal.application.services.output_naming import build_output_filename


def test_build_output_filename_cv_lowercases_company_and_slugifies():
    assert build_output_filename(kind="cv", company="Proxify", extension="pdf") == "bruno-vargas-cv-proxify.pdf"


def test_build_output_filename_cover_letter_uses_cl_prefix():
    assert build_output_filename(kind="cover_letter", company="Proxify", extension="docx") == "bruno-vargas-cl-proxify.docx"


def test_build_output_filename_replaces_whitespace_with_hyphen():
    assert build_output_filename(kind="cv", company="Acme Corp", extension="pdf") == "bruno-vargas-cv-acme-corp.pdf"


def test_build_output_filename_strips_accents():
    assert build_output_filename(kind="cv", company="Müller & Søn", extension="pdf") == "bruno-vargas-cv-muller-son.pdf"


def test_build_output_filename_keeps_alphanumeric_and_hyphens():
    assert build_output_filename(kind="cv", company="Acme.io", extension="md") == "bruno-vargas-cv-acme-io.md"


def test_build_output_filename_falls_back_to_untitled_when_company_blank():
    assert build_output_filename(kind="cv", company="", extension="pdf") == "bruno-vargas-cv-untitled.pdf"
    assert build_output_filename(kind="cv", company="   ", extension="pdf") == "bruno-vargas-cv-untitled.pdf"
    assert build_output_filename(kind="cv", company="!!!", extension="pdf") == "bruno-vargas-cv-untitled.pdf"
