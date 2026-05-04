import shutil
from pathlib import Path

import pytest

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
