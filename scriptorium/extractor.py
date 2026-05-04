from pathlib import Path

import pdfplumber

_SUPPORTED = {".pdf", ".txt", ".md"}


def extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix not in _SUPPORTED:
        raise ValueError(f"Unsupported file type: {suffix}")
    if suffix == ".pdf":
        text = _extract_pdf(file_path)
    else:
        text = file_path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"No text extracted from {file_path.name}")
    return text


def _extract_pdf(file_path: Path) -> str:
    with pdfplumber.open(file_path) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return "\n".join(pages)
