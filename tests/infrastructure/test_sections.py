from cvpal.infrastructure.parsers.sections import detect_language, split_into_sections

SPANISH_CV = """Alex Doe
Backend Developer

Resumen Profesional
Desarrollador backend con experiencia en Java.

Experiencia Profesional
Desarrollador - Empresa X — 01/2020 – Presente
  - Hizo cosas.

Educación y Certificaciones
  - Tecnicatura en Sistemas.

Habilidades Técnicas
  - Java, Python.
"""

ENGLISH_CV = """Alex Doe
Backend Developer

Professional Summary
Backend developer with experience in Java.

Professional Experience
Developer - Company X — 01/2020 - Present
  - Did things.

Education
  - Technical degree.

Technical Skills
  - Java, Python.
"""

HEADERLESS_CV = """Alex Doe
Backend developer with hands-on experience in Java and Python.
Developer - Company X - 01/2020 - Present
Did things.
"""


def test_split_detects_all_canonical_sections_spanish():
    sections = split_into_sections(SPANISH_CV)
    assert set(sections) >= {"header", "summary", "experience", "education", "skills"}


def test_split_detects_all_canonical_sections_english():
    sections = split_into_sections(ENGLISH_CV)
    assert set(sections) >= {"header", "summary", "experience", "education", "skills"}


def test_split_falls_back_to_unstructured_when_no_headers_found():
    sections = split_into_sections(HEADERLESS_CV)
    assert set(sections) == {"unstructured"}
    assert "Backend developer" in sections["unstructured"]


def test_split_tolerates_double_spaced_headers():
    text = SPANISH_CV.replace("Resumen Profesional", "Resumen  Profesional")
    sections = split_into_sections(text)
    assert "summary" in sections


def test_detect_language_spanish_from_headers():
    assert detect_language(SPANISH_CV) == "es"


def test_detect_language_english_from_headers():
    assert detect_language(ENGLISH_CV) == "en"


def test_detect_language_falls_back_to_stopwords_for_prose():
    prose = "Mi nombre es Alex y trabajé con mi equipo durante muchos años."
    assert detect_language(prose) == "es"
