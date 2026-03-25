import fitz  # PyMuPDF
from typing import List, Dict
import os

def parse_pdf(file_path: str) -> List[Dict[str, any]]:
    """
    Parses a PDF file and returns a list of dictionaries, one for each page,
    containing the page number and the text content.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    doc = None
    try:
        doc = fitz.open(file_path)
        if doc.is_closed:
            raise Exception("Failed to open document: document is closed.")
        
        pages_content = []
        for page_num in range(len(doc)):
            try:
                page = doc.load_page(page_num)
                text = page.get_text()
                pages_content.append({
                    "page_number": page_num + 1,
                    "content": text
                })
            except Exception as page_err:
                # Log or handle error for a specific page
                # We can either skip or raise
                raise Exception(f"Failed to load page {page_num + 1}: {str(page_err)}")

        return pages_content
    except fitz.FileDataError:
        raise Exception(f"Failed to parse PDF: File is not a valid PDF or is corrupted.")
    except Exception as e:
        # In a real app, log the error
        raise Exception(f"Failed to parse PDF: {str(e)}")
    finally:
        if doc:
            doc.close()
