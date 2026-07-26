"""Given a job posting and the knowledge base markdown, produces a
tailored CV - see skills/cv-generation/SKILL.md. Output is markdown text;
turning it into a real .docx/.pdf needs a DocumentRenderPort adapter,
which isn't wired to any agent yet (see domain/ports/document_render.py).
"""

from __future__ import annotations

from cvpal.application.prompts.tailoring import tailor_cv_prompt
from cvpal.domain.generation.models import DocumentFormat, TailoredDocument
from cvpal.domain.ports.job_posting_source import JobPostingSourcePort
from cvpal.domain.ports.text_completion import CompletionRequest, TextCompletionPort

_DEFAULT_LANGUAGE = "en"


def tailor_cv(
    job_posting_source: JobPostingSourcePort,
    knowledge_base_markdown: str,
    agent: TextCompletionPort,
    *,
    language_override: str | None = None,
) -> TailoredDocument:
    posting = job_posting_source.read()
    language = language_override or _DEFAULT_LANGUAGE

    prompt = tailor_cv_prompt(knowledge_base_markdown, posting.raw_text, language)
    result = agent.complete(CompletionRequest(prompt=prompt))

    return TailoredDocument(
        kind="cv",
        language=language,
        document_format=DocumentFormat.MARKDOWN,
        content=result.text.strip(),
    )
