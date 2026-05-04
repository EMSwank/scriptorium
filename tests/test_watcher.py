from pathlib import Path
from unittest.mock import patch

import pytest
from watchdog.events import DirCreatedEvent, FileCreatedEvent, FileModifiedEvent

from scriptorium.watcher import ScriptoriumHandler


@pytest.fixture
def handler(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    with patch("scriptorium.watcher.anthropic.Anthropic"):
        h = ScriptoriumHandler(wiki_dir=wiki_dir, raw_dir=raw_dir, api_key="test-key")
    return h


def test_ignores_directories(handler):
    event = DirCreatedEvent("/raw/subdir")
    with patch.object(handler, "_process") as mock_process:
        handler.on_created(event)
        mock_process.assert_not_called()


def test_ignores_dotfiles(handler):
    event = FileCreatedEvent("/raw/.DS_Store")
    with patch.object(handler, "_process") as mock_process:
        handler.on_created(event)
        mock_process.assert_not_called()


def test_ignores_unsupported_extension(handler):
    event = FileCreatedEvent("/raw/doc.docx")
    with patch.object(handler, "_process") as mock_process:
        handler.on_created(event)
        mock_process.assert_not_called()


def test_processes_txt(handler):
    event = FileCreatedEvent("/raw/doc.txt")
    with patch.object(handler, "_process") as mock_process:
        handler.on_created(event)
        mock_process.assert_called_once_with(Path("/raw/doc.txt"))


def test_processes_pdf(handler):
    event = FileCreatedEvent("/raw/report.pdf")
    with patch.object(handler, "_process") as mock_process:
        handler.on_created(event)
        mock_process.assert_called_once_with(Path("/raw/report.pdf"))


def test_processes_md(handler):
    event = FileCreatedEvent("/raw/notes.md")
    with patch.object(handler, "_process") as mock_process:
        handler.on_created(event)
        mock_process.assert_called_once_with(Path("/raw/notes.md"))


def test_processes_uppercase_extension(handler):
    event = FileCreatedEvent("/raw/report.PDF")
    with patch.object(handler, "_process") as mock_process:
        handler.on_created(event)
        mock_process.assert_called_once_with(Path("/raw/report.PDF"))


def test_on_modified_ignored(handler):
    with patch.object(handler, "_process") as mock_process:
        handler.on_modified(FileModifiedEvent("/raw/doc.txt"))
        mock_process.assert_not_called()


def test_process_calls_pipeline(handler, tmp_path):
    source = tmp_path / "raw" / "doc.txt"
    source.write_text("content", encoding="utf-8")

    with (
        patch("scriptorium.watcher.extract_text", return_value="extracted") as mock_extract,
        patch("scriptorium.watcher.load_wiki_context", return_value="context") as mock_ctx,
        patch("scriptorium.watcher.generate_note", return_value="# Note") as mock_gen,
        patch("scriptorium.watcher.write_note") as mock_write,
    ):
        handler._process(source)

    mock_extract.assert_called_once_with(source)
    mock_ctx.assert_called_once_with(handler.wiki_dir)
    mock_gen.assert_called_once_with("extracted", "doc.txt", "context", handler.client)
    mock_write.assert_called_once_with("# Note", source, handler.wiki_dir, handler.raw_dir)


def test_process_routes_errors_to_failed(handler, tmp_path):
    source = tmp_path / "raw" / "bad.txt"
    source.write_text("content", encoding="utf-8")
    err = ValueError("boom")

    with (
        patch("scriptorium.watcher.extract_text", side_effect=err),
        patch("scriptorium.watcher.move_to_failed") as mock_failed,
    ):
        handler._process(source)

    mock_failed.assert_called_once_with(source, handler.raw_dir, err)


def test_process_move_to_failed_secondary_exception_does_not_propagate(handler, tmp_path):
    source = tmp_path / "raw" / "bad.txt"
    source.write_text("content", encoding="utf-8")

    with (
        patch("scriptorium.watcher.extract_text", side_effect=ValueError("pipeline fail")),
        patch("scriptorium.watcher.move_to_failed", side_effect=OSError("disk full")),
    ):
        # Must not raise — secondary exception in move_to_failed is swallowed and logged
        handler._process(source)
