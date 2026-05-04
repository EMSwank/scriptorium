import logging
from pathlib import Path

import anthropic
from watchdog.events import FileSystemEventHandler

from scriptorium.claude import generate_note, load_wiki_context
from scriptorium.extractor import extract_text
from scriptorium.writer import move_to_failed, write_note

logger = logging.getLogger(__name__)

# Mirrors extractor._SUPPORTED — intentionally decoupled so watcher and extractor can evolve independently
_SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md"}


class ScriptoriumHandler(FileSystemEventHandler):
    def __init__(self, wiki_dir: Path, raw_dir: Path, api_key: str) -> None:
        super().__init__()
        self.wiki_dir = wiki_dir
        self.raw_dir = raw_dir
        self.client = anthropic.Anthropic(api_key=api_key)

    def on_created(self, event) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.name.startswith("."):
            return
        if path.suffix.lower() not in _SUPPORTED_SUFFIXES:
            return
        logger.info("New file: %s", path.name)
        self._process(path)

    def _process(self, path: Path) -> None:
        try:
            text = extract_text(path)
            wiki_context = load_wiki_context(self.wiki_dir)
            content = generate_note(text, path.name, wiki_context, self.client)
            write_note(content, path, self.wiki_dir, self.raw_dir)
        except Exception as e:
            logger.exception("Error processing %s", path.name)
            try:
                move_to_failed(path, self.raw_dir, e)
            except Exception:
                logger.exception("Failed to route %s to failed/", path.name)
