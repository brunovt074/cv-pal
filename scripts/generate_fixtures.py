"""Generate tests/fixtures/* from scratch using a fictitious persona.

Run after cloning to (re)produce the binary test fixtures without ever
storing a real person's CV in the repo. Uses the project's own rendering
pipeline (`LocalDocumentRenderer` / `markdown_to_docx`) for the .docx and
.pdf fixtures - real hyperlink annotations included, same code path
production output goes through - and `odfpy` directly for the one .odt
fixture (no ODT writer exists elsewhere in the codebase).

Every fixture here backs an assertion in tests/infrastructure/test_dispatch.py -
see that file before changing content shapes (section headers, language,
messiness, filename) as they're what the assertions actually check.
"""

from __future__ import annotations

from pathlib import Path

from odf.opendocument import OpenDocumentText
from odf.text import A, P

from cvpal.domain.generation.models import DocumentFormat
from cvpal.infrastructure.rendering.local_document_renderer import LocalDocumentRenderer

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

_CLEAN_RECENT_MD = """\
# Alex Doe
Backend Developer

[LinkedIn](https://www.linkedin.com/in/alex-doe-dev/) | [GitHub](https://github.com/alexdoe)

## Resumen Profesional
Desarrollador backend con 6 años de experiencia en sistemas distribuidos usando Python y Go.

## Experiencia Profesional
### Ingeniero Backend Senior - Example Corp -- 2022 - Presente
- Lideró la migración de un monolito a microservicios basados en eventos.
- Redujo la latencia p99 en un 40%.

### Desarrollador Backend - Startup Inc -- 2019 - 2022
- Construyó el servicio de pagos que procesa 200k transacciones diarias.

## Educación
- Licenciatura en Ciencias de la Computación - Universidad Estatal (2019)

## Habilidades Técnicas
- Python, Go, Kafka, PostgreSQL, Kubernetes

## Idiomas
- Español (nativo), Inglés (profesional)
"""

_OLDER_MESSY_MD = """\
Alex Doe. Backend developer with six years across distributed systems for \
payments and internal tooling. Worked mostly with Python and some Go, plus \
a good deal of on-call rotation and infra debugging over the years, \
including a memorable weekend fixing a stuck payments queue. Previously \
did a two year contract doing Django work for a small logistics company \
before that. Studied computer science at a state university, graduated in \
twenty nineteen. Comfortable in English and Spanish. Reachable at alex dot \
doe at example dot com.
"""

_SAMPLE_DOCX_MD = """\
# Alex Doe
Backend Developer

[LinkedIn](https://www.linkedin.com/in/alex-doe-dev/) | [GitHub](https://github.com/alexdoe)

## Professional Summary
Backend engineer focused on distributed systems and reliability.

## Experience
### Senior Backend Engineer - Example Corp -- 2022 - Present
- Led the migration to event-driven microservices.
- Reduced p99 latency by 40%.

## Education
- B.Sc. Computer Science - State University (2019)

## Skills
- Python, Go, Kafka, PostgreSQL
"""

_COVER_LETTER_MD = """\
Dear Hiring Manager,

I'm excited to apply for the Backend Engineer role at Example Corp. Over \
the past six years I've built and operated distributed systems handling \
millions of daily requests, and I'd love to bring that experience to your \
team.

I look forward to speaking with you soon.

Alex Doe
"""


def _generate_pdf_and_docx_fixtures() -> None:
    renderer = LocalDocumentRenderer()
    renderer.render(
        _CLEAN_RECENT_MD, document_format=DocumentFormat.PDF, output_path=FIXTURES_DIR / "clean-recent.pdf"
    )
    renderer.render(
        _OLDER_MESSY_MD, document_format=DocumentFormat.PDF, output_path=FIXTURES_DIR / "older-messy.pdf"
    )
    renderer.render(
        _COVER_LETTER_MD, document_format=DocumentFormat.PDF, output_path=FIXTURES_DIR / "cover-letter.pdf"
    )
    renderer.render(
        _SAMPLE_DOCX_MD, document_format=DocumentFormat.DOCX, output_path=FIXTURES_DIR / "sample.docx"
    )


def _generate_odt_fixture() -> None:
    doc = OpenDocumentText()

    def add_para(text: str = "") -> None:
        doc.text.addElement(P(text=text))

    add_para("Alex Doe")
    add_para("Backend Developer")
    link_paragraph = P()
    link_paragraph.addElement(A(href="https://www.linkedin.com/in/alex-doe-dev/", text="LinkedIn"))
    doc.text.addElement(link_paragraph)
    add_para()
    add_para("Professional Summary")
    add_para(
        "Backend engineer with experience across distributed systems, APIs, "
        "and cloud infrastructure."
    )
    add_para()
    add_para("Experience")
    add_para("Backend Developer - Example Corp - 2019 - 2022")
    add_para("Built and maintained internal tooling used by three product teams.")
    add_para()
    add_para("Education")
    add_para("B.Sc. Computer Science - State University")

    doc.save(str(FIXTURES_DIR / "sample.odt"))


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    _generate_pdf_and_docx_fixtures()
    _generate_odt_fixture()
    for name in ("clean-recent.pdf", "older-messy.pdf", "cover-letter.pdf", "sample.docx", "sample.odt"):
        path = FIXTURES_DIR / name
        print(f"wrote {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
