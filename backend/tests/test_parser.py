from unittest.mock import MagicMock, patch
import pytest
import fitz
from backend.app.services.parser import parse_pdf

def test_parse_pdf_success():
    # Setup mock for PyMuPDF
    mock_doc = MagicMock()
    mock_doc.__len__.return_value = 2  # 2 pages
    mock_doc.is_closed = False
    
    mock_page1 = MagicMock()
    mock_page1.get_text.return_value = "Page 1 text content"
    
    mock_page2 = MagicMock()
    mock_page2.get_text.return_value = "Page 2 text content"
    
    # Mock doc.load_page(0) and doc.load_page(1)
    mock_doc.load_page.side_effect = [mock_page1, mock_page2]
    
    with patch("os.path.exists", return_value=True):
        with patch("fitz.open", return_value=mock_doc):
            pages = parse_pdf("sample.pdf")
            
            assert len(pages) == 2
            assert pages[0]["page_number"] == 1
            assert pages[0]["content"] == "Page 1 text content"
            assert pages[1]["page_number"] == 2
            assert pages[1]["content"] == "Page 2 text content"
            
            # Verify calls
            mock_doc.close.assert_called_once()

def test_parse_pdf_not_found():
    with patch("os.path.exists", return_value=False):
        with pytest.raises(FileNotFoundError) as excinfo:
            parse_pdf("nonexistent.pdf")
        assert "does not exist" in str(excinfo.value)

def test_parse_pdf_corrupted():
    with patch("os.path.exists", return_value=True):
        with patch("fitz.open", side_effect=fitz.FileDataError("File is corrupted")):
            with pytest.raises(Exception) as excinfo:
                parse_pdf("corrupted.pdf")
            assert "is not a valid PDF or is corrupted" in str(excinfo.value)

def test_parse_pdf_page_load_failure():
    # Setup mock for PyMuPDF
    mock_doc = MagicMock()
    mock_doc.__len__.return_value = 1
    mock_doc.is_closed = False
    mock_doc.load_page.side_effect = Exception("Failed to load page")
    
    with patch("os.path.exists", return_value=True):
        with patch("fitz.open", return_value=mock_doc):
            with pytest.raises(Exception) as excinfo:
                parse_pdf("fail_page.pdf")
            assert "Failed to load page 1" in str(excinfo.value)
            mock_doc.close.assert_called_once()
