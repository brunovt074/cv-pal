from cvpal.application.use_cases.clean_outputs import clean_outputs


def _seed_outputs(outputs_dir, names):
    outputs_dir.mkdir(parents=True, exist_ok=True)
    for name in names:
        (outputs_dir / name).write_text("x")


def test_clean_outputs_deletes_single_named_file(tmp_path):
    _seed_outputs(tmp_path, ["alex-doe-cv-proxify.pdf", "alex-doe-cv-other.docx"])
    result = clean_outputs(outputs_dir=tmp_path, filename="alex-doe-cv-proxify.pdf", remove_all=False)
    assert [p.name for p in result.deleted] == ["alex-doe-cv-proxify.pdf"]
    assert (tmp_path / "alex-doe-cv-other.docx").exists()
    assert not (tmp_path / "alex-doe-cv-proxify.pdf").exists()


def test_clean_outputs_remove_all_wipes_every_file(tmp_path):
    _seed_outputs(
        tmp_path,
        ["a.pdf", "b.docx", "c.md"],
    )
    result = clean_outputs(outputs_dir=tmp_path, filename=None, remove_all=True)
    assert sorted(p.name for p in result.deleted) == ["a.pdf", "b.docx", "c.md"]
    assert list(tmp_path.iterdir()) == []


def test_clean_outputs_remove_all_recurses_into_cover_letter_subfolder(tmp_path):
    _seed_outputs(tmp_path, ["alex-doe-cv-proxify.pdf"])
    cl_dir = tmp_path / "cover-letter"
    cl_dir.mkdir()
    (cl_dir / "alex-doe-cl-proxify.pdf").write_text("x")
    (cl_dir / "alex-doe-cl-other.docx").write_text("x")
    result = clean_outputs(outputs_dir=tmp_path, filename=None, remove_all=True)
    assert sorted(p.name for p in result.deleted) == [
        "alex-doe-cl-other.docx",
        "alex-doe-cl-proxify.pdf",
        "alex-doe-cv-proxify.pdf",
    ]
    assert not cl_dir.exists()
    assert list(tmp_path.iterdir()) == []


def test_clean_outputs_remove_all_deletes_files_in_arbitrary_subdirectories(tmp_path):
    _seed_outputs(tmp_path, ["alex-doe-cv-proxify.pdf"])
    subdir = tmp_path / "unrelated"
    subdir.mkdir()
    (subdir / "should-be-removed.pdf").write_text("x")
    result = clean_outputs(outputs_dir=tmp_path, filename=None, remove_all=True)
    assert sorted(p.name for p in result.deleted) == [
        "alex-doe-cv-proxify.pdf",
        "should-be-removed.pdf",
    ]
    assert list(tmp_path.iterdir()) == []


def test_clean_outputs_rejects_missing_file(tmp_path):
    _seed_outputs(tmp_path, ["real.pdf"])
    result = clean_outputs(outputs_dir=tmp_path, filename="ghost.pdf", remove_all=False)
    assert result.deleted == []
    assert "not found" in (result.reason or "").lower()
    assert (tmp_path / "real.pdf").exists()


def test_clean_outputs_refuses_when_neither_argument_supplied(tmp_path):
    result = clean_outputs(outputs_dir=tmp_path, filename=None, remove_all=False)
    assert result.deleted == []
    assert "pass a file name" in (result.reason or "").lower()


def test_clean_outputs_refuses_when_both_arguments_supplied(tmp_path):
    result = clean_outputs(outputs_dir=tmp_path, filename="x.pdf", remove_all=True)
    assert result.deleted == []
    assert "not both" in (result.reason or "").lower()


def test_clean_outputs_refuses_path_escape(tmp_path):
    _seed_outputs(tmp_path, ["safe.pdf"])
    outside = tmp_path.parent / "should-not-touch.txt"
    outside.write_text("do not delete")
    try:
        result = clean_outputs(outputs_dir=tmp_path, filename="../should-not-touch.txt", remove_all=False)
        assert result.deleted == []
        assert "escapes" in (result.reason or "").lower()
        assert outside.exists()
    finally:
        outside.unlink(missing_ok=True)


def test_clean_outputs_refuses_directory_target(tmp_path):
    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "nested.pdf").write_text("x")
    result = clean_outputs(outputs_dir=tmp_path, filename="sub", remove_all=False)
    assert result.deleted == []
    assert "not a regular file" in (result.reason or "").lower()
    assert subdir.exists()
