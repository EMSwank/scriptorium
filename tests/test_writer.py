from pathlib import Path

from scriptorium.writer import move_to_failed, write_note


def _make_dirs(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "processed").mkdir()
    (raw_dir / "failed").mkdir()
    return wiki_dir, raw_dir


def test_write_note_creates_md(tmp_path):
    wiki_dir, raw_dir = _make_dirs(tmp_path)
    source = raw_dir / "doc.txt"
    source.write_text("source content", encoding="utf-8")

    write_note("# Note\n\nContent", source, wiki_dir, raw_dir)

    output = wiki_dir / "doc.md"
    assert output.exists()
    assert output.read_text(encoding="utf-8") == "# Note\n\nContent"


def test_write_note_moves_to_processed(tmp_path):
    wiki_dir, raw_dir = _make_dirs(tmp_path)
    source = raw_dir / "doc.txt"
    source.write_text("source content", encoding="utf-8")

    write_note("# Note", source, wiki_dir, raw_dir)

    assert not source.exists()
    assert (raw_dir / "processed" / "doc.txt").exists()


def test_write_note_collision_creates_second_file(tmp_path):
    wiki_dir, raw_dir = _make_dirs(tmp_path)
    (wiki_dir / "doc.md").write_text("existing note", encoding="utf-8")

    # Move processed file back to simulate second drop of same name
    source = raw_dir / "doc.txt"
    source.write_text("second source", encoding="utf-8")

    write_note("# Note 2", source, wiki_dir, raw_dir)

    md_files = sorted(wiki_dir.glob("*.md"))
    assert len(md_files) == 2
    assert md_files[0].name == "doc.md"  # original untouched
    assert md_files[0].read_text(encoding="utf-8") == "existing note"
    assert md_files[1].read_text(encoding="utf-8") == "# Note 2"


def test_move_to_failed_moves_file(tmp_path):
    wiki_dir, raw_dir = _make_dirs(tmp_path)
    source = raw_dir / "bad.txt"
    source.write_text("bad content", encoding="utf-8")

    try:
        raise ValueError("something broke")
    except ValueError as e:
        move_to_failed(source, raw_dir, e)

    assert not source.exists()
    assert (raw_dir / "failed" / "bad.txt").exists()


def test_move_to_failed_writes_error_log(tmp_path):
    wiki_dir, raw_dir = _make_dirs(tmp_path)
    source = raw_dir / "bad.txt"
    source.write_text("bad content", encoding="utf-8")

    try:
        raise ValueError("something broke")
    except ValueError as e:
        move_to_failed(source, raw_dir, e)

    log_path = raw_dir / "failed" / "bad.txt.error.log"
    assert log_path.exists()
    log_text = log_path.read_text(encoding="utf-8")
    assert "Timestamp:" in log_text
    assert "bad.txt" in log_text
    assert "ValueError" in log_text
    assert "something broke" in log_text
    assert "Traceback" in log_text


def test_move_to_failed_creates_failed_dir_if_missing(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    # No failed/ dir — writer must create it
    source = raw_dir / "bad.txt"
    source.write_text("content", encoding="utf-8")

    try:
        raise RuntimeError("oops")
    except RuntimeError as e:
        move_to_failed(source, raw_dir, e)

    assert (raw_dir / "failed" / "bad.txt").exists()


def test_write_note_no_processed_collision(tmp_path):
    wiki_dir, raw_dir = _make_dirs(tmp_path)

    # First file — lands in processed/doc.txt
    source1 = raw_dir / "doc.txt"
    source1.write_text("first", encoding="utf-8")
    write_note("# Note 1", source1, wiki_dir, raw_dir)

    # Second drop with same name while processed/doc.txt still exists
    source2 = raw_dir / "doc.txt"
    source2.write_text("second", encoding="utf-8")
    write_note("# Note 2", source2, wiki_dir, raw_dir)

    processed_files = list((raw_dir / "processed").glob("doc*"))
    assert len(processed_files) == 2
    # Original processed copy must not have been overwritten
    assert (raw_dir / "processed" / "doc.txt").read_text(encoding="utf-8") == "first"


def test_move_to_failed_no_collision(tmp_path):
    wiki_dir, raw_dir = _make_dirs(tmp_path)

    # Pre-populate failed/ with an existing file of the same name
    existing = raw_dir / "failed" / "bad.txt"
    existing.write_text("original failed content", encoding="utf-8")

    source = raw_dir / "bad.txt"
    source.write_text("new bad content", encoding="utf-8")

    try:
        raise ValueError("second failure")
    except ValueError as e:
        move_to_failed(source, raw_dir, e)

    # Original file in failed/ must be untouched
    assert existing.read_text(encoding="utf-8") == "original failed content"

    # A renamed copy must exist
    renamed_files = [
        f for f in (raw_dir / "failed").iterdir()
        if f.name != "bad.txt" and f.suffix == ".txt"
    ]
    assert len(renamed_files) == 1

    # The .error.log must match the renamed file's name (not the original)
    renamed_name = renamed_files[0].name
    error_log = raw_dir / "failed" / f"{renamed_name}.error.log"
    assert error_log.exists(), f"Expected error log: {renamed_name}.error.log"
    log_text = error_log.read_text(encoding="utf-8")
    assert "ValueError" in log_text
    assert "second failure" in log_text
