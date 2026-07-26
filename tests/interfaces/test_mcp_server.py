import json

from cvpal.config import Settings
from cvpal.container import Container
from cvpal.domain.documents.models import RawDocument
from cvpal.domain.errors import JobPostingFetchError
from cvpal.domain.knowledge.models import ExperienceBullet, KnowledgeBase, PersonalDataField
from cvpal.domain.knowledge.voice import VoiceProfile
from cvpal.interfaces.mcp import server
from tests.fakes.fake_text_agent import FakeTextAgent


def _settings(tmp_path) -> Settings:
    settings = Settings()
    settings.data_dir = tmp_path
    settings.ingested_json = tmp_path / "ingested.json"
    settings.knowledge_base_md = tmp_path / "knowledge-base.md"
    settings.checkpoint_dir = tmp_path / ".checkpoints"
    settings.raw_dir = tmp_path / "raw"
    settings.outputs_dir = tmp_path / "outputs"
    return settings


def _container(tmp_path) -> Container:
    return Container(_settings(tmp_path))


def _seed_kb(container: Container) -> KnowledgeBase:
    kb = KnowledgeBase(
        personal_data=[PersonalDataField(field="name", value="Test Author", source_files=["a.pdf"])],
        experience=[
            ExperienceBullet(
                company="Acme", role="Dev", start_date="2020", end_date="Present", bullet="Did a thing"
            )
        ],
        voice_profile=VoiceProfile(opening_style="Direct", tone_summary=["direct"]),
    )
    container.knowledge_repository.save(kb)
    return kb


# --- cv_pal prompt ---


def test_cv_pal_reports_missing_knowledge_base(tmp_path):
    container = _container(tmp_path)
    result = server._cv_pal(container, "some posting", "", "", "")
    assert result == server._NO_KB_MESSAGE


def test_cv_pal_requires_exactly_one_of_text_file_or_url(tmp_path):
    container = _container(tmp_path)
    _seed_kb(container)
    assert "exactly one" in server._cv_pal(container, "", "", "", "")
    assert "exactly one" in server._cv_pal(container, "text", "file.md", "", "")
    assert "exactly one" in server._cv_pal(container, "text", "", "https://example.com/job", "")
    assert "exactly one" in server._cv_pal(container, "", "file.md", "https://example.com/job", "")


def test_cv_pal_assembles_prompt_with_material_and_posting(tmp_path):
    container = _container(tmp_path)
    _seed_kb(container)
    result = server._cv_pal(container, "UNIQUE_POSTING_MARKER", "", "", "en")
    assert "UNIQUE_POSTING_MARKER" in result
    assert "Acme" in result
    assert "Write in en" in result


def test_cv_pal_defaults_to_english_even_for_a_non_english_posting(tmp_path):
    container = _container(tmp_path)
    _seed_kb(container)
    result = server._cv_pal(
        container, "Se busca desarrollador backend con experiencia en Java", "", "", ""
    )
    assert "Write in en" in result


def test_cv_pal_reads_posting_from_file(tmp_path):
    container = _container(tmp_path)
    _seed_kb(container)
    posting_file = tmp_path / "posting.txt"
    posting_file.write_text("FILE_POSTING_MARKER")
    result = server._cv_pal(container, "", str(posting_file), "", "es")
    assert "FILE_POSTING_MARKER" in result
    assert "Write in es" in result


def test_cv_pal_reads_posting_from_url(tmp_path, monkeypatch):
    container = _container(tmp_path)
    _seed_kb(container)

    class _FakeWebContent:
        def fetch(self, url: str) -> str:
            assert url == "https://example.com/job"
            return "URL_POSTING_MARKER"

    monkeypatch.setattr(type(container), "web_content", property(lambda self: _FakeWebContent()))

    result = server._cv_pal(container, "", "", "https://example.com/job", "en")
    assert "URL_POSTING_MARKER" in result


def test_cv_pal_reports_fetch_failure_from_url(tmp_path, monkeypatch):
    container = _container(tmp_path)
    _seed_kb(container)

    class _FailingWebContent:
        def fetch(self, url: str) -> str:
            raise JobPostingFetchError(url, "connection refused")

    monkeypatch.setattr(type(container), "web_content", property(lambda self: _FailingWebContent()))

    result = server._cv_pal(container, "", "", "https://example.com/job", "en")
    assert "connection refused" in result


# --- get_cv_material ---


def test_get_cv_material_reports_missing_knowledge_base(tmp_path):
    assert server._get_cv_material(_container(tmp_path)) == server._NO_KB_MESSAGE


def test_get_cv_material_returns_lean_view(tmp_path):
    container = _container(tmp_path)
    _seed_kb(container)
    result = server._get_cv_material(container)
    assert "Acme" in result
    assert "a.pdf" not in result


# --- get_knowledge_base ---


def test_get_knowledge_base_reports_missing(tmp_path):
    assert server._get_knowledge_base(_container(tmp_path), "") == server._NO_KB_MESSAGE


def test_get_knowledge_base_full_document(tmp_path):
    container = _container(tmp_path)
    _seed_kb(container)
    result = server._get_knowledge_base(container, "")
    assert "a.pdf" in result  # full view keeps provenance


def test_get_knowledge_base_single_section(tmp_path):
    container = _container(tmp_path)
    _seed_kb(container)
    result = server._get_knowledge_base(container, "experience")
    assert "Acme" in result
    assert "Personal Data" not in result


def test_get_knowledge_base_unknown_section(tmp_path):
    container = _container(tmp_path)
    _seed_kb(container)
    result = server._get_knowledge_base(container, "not-a-real-section")
    assert "No section" in result


# --- update_knowledge_base ---


def test_update_knowledge_base_reports_missing(tmp_path):
    assert server._update_knowledge_base(_container(tmp_path), "new content", False) == server._NO_KB_MESSAGE


def test_update_knowledge_base_writes_and_backs_up(tmp_path):
    container = _container(tmp_path)
    _seed_kb(container)
    new_markdown = container.settings.knowledge_base_md.read_text().replace("Acme", "NewCo")

    result = server._update_knowledge_base(container, new_markdown, False)

    assert "updated" in result.lower()
    assert "NewCo" in container.settings.knowledge_base_md.read_text()
    backups = list(tmp_path.glob("knowledge-base.md.bak-*"))
    assert len(backups) == 1
    assert "Acme" in backups[0].read_text()


def test_update_knowledge_base_rejects_near_total_wipe_without_force(tmp_path):
    container = _container(tmp_path)
    _seed_kb(container)
    result = server._update_knowledge_base(container, "# empty\n", False)
    assert "rejected" in result.lower()
    assert "Acme" in container.settings.knowledge_base_md.read_text()  # untouched


def test_update_knowledge_base_force_overrides_rejection(tmp_path):
    container = _container(tmp_path)
    _seed_kb(container)
    result = server._update_knowledge_base(container, "# empty\n", True)
    assert "updated" in result.lower()


# --- audit_knowledge_base ---


def test_audit_knowledge_base_reports_missing(tmp_path):
    assert server._audit_knowledge_base(_container(tmp_path)) == server._NO_KB_MESSAGE


def test_audit_knowledge_base_no_inconsistencies(tmp_path):
    container = _container(tmp_path)
    _seed_kb(container)
    assert server._audit_knowledge_base(container) == "No inconsistencies found."


def test_audit_knowledge_base_reports_inconsistencies(tmp_path):
    container = _container(tmp_path)
    kb = KnowledgeBase(
        personal_data=[
            PersonalDataField(field="phone", value="+1 (current)"),
            PersonalDataField(field="phone", value="+2 (previous)"),
        ]
    )
    container.knowledge_repository.save(kb)
    result = server._audit_knowledge_base(container)
    assert "phone" in result


# --- ingest_corpus ---


def test_ingest_corpus_reports_zero_documents_for_empty_dir(tmp_path):
    container = _container(tmp_path)
    container.settings.raw_dir.mkdir(parents=True, exist_ok=True)
    result = server._ingest_corpus(container)
    assert "Ingested 0 documents" in result
    assert "0 unchanged" in result
    assert "0 parsed" in result


# --- rebuild_knowledge_base ---


def test_rebuild_knowledge_base_requires_ingest_first(tmp_path):
    container = _container(tmp_path)
    assert "ingest_corpus" in server._rebuild_knowledge_base(container)


def test_rebuild_knowledge_base_makes_agent_calls_and_reports_rebuilt(tmp_path):
    container = _container(tmp_path)
    docs = [
        RawDocument(
            source_file="a.pdf",
            doc_kind="cv",
            source_language="en",
            sections={"skills": "Java, Python"},
        )
    ]
    container.raw_document_repository.save(docs)
    container._agent = FakeTextAgent(
        [json.dumps([{"skill": "Java", "category": "language", "source_files": ["a.pdf"]}])]
    )

    result = server._rebuild_knowledge_base(container)

    # First-ever build: every section is a checkpoint miss (even ones with
    # no input, which short-circuit to an empty result without an agent
    # call) - "skills" is the one that actually consumed the FakeTextAgent
    # response, confirmed by the resulting knowledge base content.
    assert "skills" in result
    assert container.knowledge_repository.exists()
    assert container.knowledge_repository.load().skills[0].skill == "Java"


def test_rebuild_knowledge_base_is_a_no_op_when_nothing_changed(tmp_path):
    container = _container(tmp_path)
    docs = [
        RawDocument(
            source_file="a.pdf",
            doc_kind="cv",
            source_language="en",
            sections={"skills": "Java, Python"},
        )
    ]
    container.raw_document_repository.save(docs)
    container._agent = FakeTextAgent(
        [json.dumps([{"skill": "Java", "category": "language", "source_files": ["a.pdf"]}])]
    )
    server._rebuild_knowledge_base(container)

    container._agent = FakeTextAgent([])  # would raise if called
    result = server._rebuild_knowledge_base(container)

    assert "already up to date" in result.lower()
