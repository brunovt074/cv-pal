"""Render the cover letter markdown to DOCX using cv-pal's local renderer."""
from __future__ import annotations

from cvpal.config import get_settings
from cvpal.container import Container
from cvpal.domain.generation.models import DocumentFormat


def main() -> None:
    settings = get_settings()
    container = Container(settings)

    md_path = settings.outputs_dir / "Bruno-Vargas-Tettamanti-cover-letter.md"
    docx_path = settings.outputs_dir / "Bruno-Vargas-Tettamanti-cover-letter.docx"

    if not md_path.exists():
        raise SystemExit(f"missing markdown source: {md_path}")

    rendered = container.document_renderer.render(
        md_path.read_text(),
        document_format=DocumentFormat.DOCX,
        output_path=docx_path,
    )
    print(f"Wrote {rendered} ({rendered.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
