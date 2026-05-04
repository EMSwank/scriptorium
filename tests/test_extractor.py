from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scriptorium.extractor import extract_text


def test_extract_txt(tmp_path):
    f = tmp_path / "doc.txt"
    f.write_text("hello world", encoding="utf-8")
    assert extract_text(f) == "hello world"


def test_extract_md(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("# Title\n\nContent here.", encoding="utf-8")
    assert extract_text(f) == "# Title\n\nContent here."


def test_extract_pdf(tmp_path):
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Page one text"
    mock_pdf = MagicMock()
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)
    mock_pdf.pages = [mock_page]

    with patch("scriptorium.extractor.pdfplumber.open", return_value=mock_pdf):
        result = extract_text(pdf_path)

    assert result == "Page one text"


def test_extract_pdf_multiple_pages(tmp_path):
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    page1 = MagicMock()
    page1.extract_text.return_value = "Page one"
    page2 = MagicMock()
    page2.extract_text.return_value = "Page two"
    page3 = MagicMock()
    page3.extract_text.return_value = None  # blank page

    mock_pdf = MagicMock()
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)
    mock_pdf.pages = [page1, page2, page3]

    with patch("scriptorium.extractor.pdfplumber.open", return_value=mock_pdf):
        result = extract_text(pdf_path)

    assert result == "Page one\nPage two\n"


def test_extract_unsupported_raises(tmp_path):
    f = tmp_path / "doc.docx"
    f.write_bytes(b"content")
    with pytest.raises(ValueError, match="Unsupported file type: .docx"):
        extract_text(f)
