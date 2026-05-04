import logging
import os
import sys
import time
from pathlib import Path

from watchdog.observers import Observer

from scriptorium.watcher import ScriptoriumHandler

RAW_DIR = Path(
    "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/wiki/raw"
).expanduser()
WIKI_DIR = Path(
    "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/wiki"
).expanduser()


def setup_logging() -> None:
    log_dir = Path("~/Library/Logs").expanduser()
    log_dir.mkdir(exist_ok=True)
    level = logging.DEBUG if os.environ.get("SCRIPTORIUM_DEBUG") else logging.INFO
    logging.basicConfig(
        filename=log_dir / "scriptorium.log",
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("Error: ANTHROPIC_API_KEY environment variable is not set")

    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Scriptorium")

    (RAW_DIR / "processed").mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "failed").mkdir(parents=True, exist_ok=True)

    handler = ScriptoriumHandler(wiki_dir=WIKI_DIR, raw_dir=RAW_DIR, api_key=api_key)
    observer = Observer()
    observer.schedule(handler, str(RAW_DIR), recursive=False)
    observer.start()
    logger.info("Watching: %s", RAW_DIR)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
