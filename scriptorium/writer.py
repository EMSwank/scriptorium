import logging
import shutil
import traceback
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def write_note(content: str, source_path: Path, wiki_dir: Path, raw_dir: Path) -> None:
    stem = source_path.stem
    output_path = wiki_dir / f"{stem}.md"
    if output_path.exists():
        ts = datetime.now().strftime("%Y%m%dT%H%M%S%f")
        output_path = wiki_dir / f"{stem}_{ts}.md"

    output_path.write_text(content, encoding="utf-8")
    logger.info("Wrote note: %s", output_path.name)

    processed_dir = raw_dir / "processed"
    processed_dir.mkdir(exist_ok=True)
    dest = processed_dir / source_path.name
    if dest.exists():
        ts = datetime.now().strftime("%Y%m%dT%H%M%S%f")
        dest = processed_dir / f"{source_path.stem}_{ts}{source_path.suffix}"
    shutil.move(str(source_path), str(dest))
    logger.info("Moved %s → processed/", source_path.name)


def move_to_failed(source_path: Path, raw_dir: Path, error: Exception) -> None:
    failed_dir = raw_dir / "failed"
    failed_dir.mkdir(exist_ok=True)

    dest = failed_dir / source_path.name
    if dest.exists():
        ts = datetime.now().strftime("%Y%m%dT%H%M%S%f")
        dest = failed_dir / f"{source_path.stem}_{ts}{source_path.suffix}"

    shutil.move(str(source_path), str(dest))

    error_log = failed_dir / f"{dest.name}.error.log"
    tb_str = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )
    error_log.write_text(
        f"Timestamp: {datetime.now().isoformat()}\n"
        f"File: {source_path.name}\n"
        f"Error: {type(error).__name__}: {error}\n"
        f"Traceback:\n{tb_str}\n",
        encoding="utf-8",
    )
    logger.error("Failed: %s — %s: %s", source_path.name, type(error).__name__, error)
