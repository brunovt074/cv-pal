import json

from cvpal.application.use_cases.build_knowledge_base import build_knowledge_base
from cvpal.domain.documents.models import RawDocument
from cvpal.infrastructure.persistence.file_checkpoint_store import FileCheckpointStore
from tests.fakes.fake_text_agent import FakeTextAgent

_DOCS = [
    RawDocument(
        source_file="a.pdf",
        doc_kind="cv",
        source_language="en",
        sections={
            "header": "Alex Doe\nBackend Developer",
            "links": "linkedin: https://www.linkedin.com/in/alex-doe-dev/",
            "summary": "Backend developer with Java experience.",
            "experience": "Developer - Acme - 01/2020 - Present\n- Built REST APIs",
            "education": "Tecnicatura en Sistemas - UTN",
            "skills": "Java, Spring Boot, PostgreSQL",
            "projects": "Personal finance tracker built with FastAPI",
            "languages": "Spanish (native), English (B2)",
        },
    ),
    RawDocument(
        source_file="cover-letter.pdf",
        doc_kind="cover_letter",
        source_language="en",
        unstructured="Dear hiring manager, I am excited to apply...",
    ),
]

_ALL_SECTIONS = [
    "personal_data",
    "summaries",
    "experience",
    "education_certifications",
    "skills",
    "projects",
    "languages",
    "voice_profile",
]

_RESPONSES = [
    json.dumps([{"field": "name", "value": "Alex Doe", "source_files": ["a.pdf"]}]),
    json.dumps([{"variant_label": "Backend", "text": "Backend developer.", "source_files": ["a.pdf"]}]),
    json.dumps(
        [
            {
                "company": "Acme",
                "role": "Developer",
                "start_date": "01/2020",
                "end_date": "Present",
                "bullet": "Built REST APIs",
                "tech_tags": ["Java"],
                "source_files": ["a.pdf"],
            }
        ]
    ),
    json.dumps(
        {
            "education": [
                {"institution": "UTN", "program": "Tecnicatura", "source_files": ["a.pdf"]}
            ],
            "certifications": [],
        }
    ),
    json.dumps(
        [{"skill": "Java", "category": "language", "source_files": ["a.pdf"]}]
    ),
    json.dumps(
        [{"name": "Finance tracker", "description": "Built with FastAPI", "source_files": ["a.pdf"]}]
    ),
    json.dumps([{"language": "English", "level": "B2", "source_files": ["a.pdf"]}]),
    json.dumps(
        {
            "opening_style": "Direct enthusiasm",
            "closing_style": "Thanks for your time",
            "sentence_rhythm": "Short",
            "recurring_phrases": ["I am excited to"],
            "avoided_patterns": "Buzzwords",
            "language_specific_traits": "B2 technical English",
            "tone_summary": ["direct", "enthusiastic"],
        }
    ),
]


def test_build_knowledge_base_assembles_all_sections(tmp_path):
    agent = FakeTextAgent(list(_RESPONSES))
    store = FileCheckpointStore(tmp_path)

    report = build_knowledge_base(_DOCS, agent, "fake-agent", store)
    kb = report.knowledge_base

    assert kb.personal_data[0].field == "name"
    assert kb.summaries[0].variant_label == "Backend"
    assert kb.experience[0].company == "Acme"
    assert kb.education[0].institution == "UTN"
    assert kb.certifications == []
    assert kb.skills[0].skill == "Java"
    assert kb.projects[0].name == "Finance tracker"
    assert kb.languages[0].language == "English"
    assert kb.voice_profile is not None
    assert kb.voice_profile.tone_summary == ["direct", "enthusiastic"]
    assert set(report.rebuilt_sections) == set(_ALL_SECTIONS)
    assert report.skipped_sections == []


def test_build_knowledge_base_resumes_from_checkpoints_without_recalling_agent(tmp_path):
    agent = FakeTextAgent(list(_RESPONSES))
    store = FileCheckpointStore(tmp_path)
    build_knowledge_base(_DOCS, agent, "fake-agent", store)

    agent_second_run = FakeTextAgent([])  # would raise if called
    report = build_knowledge_base(_DOCS, agent_second_run, "fake-agent", store)

    assert report.knowledge_base.personal_data[0].field == "name"
    assert agent_second_run.requests == []
    assert report.rebuilt_sections == []
    assert set(report.skipped_sections) == set(_ALL_SECTIONS)


def test_build_knowledge_base_rebuilds_only_the_section_whose_input_changed(tmp_path):
    agent = FakeTextAgent(list(_RESPONSES))
    store = FileCheckpointStore(tmp_path)
    build_knowledge_base(_DOCS, agent, "fake-agent", store)

    changed_docs = [
        _DOCS[0].model_copy(
            update={"sections": {**_DOCS[0].sections, "skills": "Java, Spring Boot, PostgreSQL, Kotlin"}}
        ),
        _DOCS[1],
    ]
    agent_second_run = FakeTextAgent(
        [json.dumps([{"skill": "Kotlin", "category": "language", "source_files": ["a.pdf"]}])]
    )

    report = build_knowledge_base(changed_docs, agent_second_run, "fake-agent", store)

    assert report.rebuilt_sections == ["skills"]
    assert set(report.skipped_sections) == set(_ALL_SECTIONS) - {"skills"}
    assert report.knowledge_base.skills[0].skill == "Kotlin"
    assert len(agent_second_run.requests) == 1
