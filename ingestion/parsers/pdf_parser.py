import os
from typing import List, Dict, Any
from pypdf import PdfReader

def parse_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Reads a PDF and returns a list of dictionaries with text and metadata.
    Format:
    {
        "text": str,
        "metadata": {
            "source": str (filename),
            "type": "pdf",
            "page": int (1-based)
        }
    }
    """
    filename = os.path.basename(pdf_path)
    print(f"Parsing PDF: {filename}")
    reader = PdfReader(pdf_path)
    results = []

    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        # Normalize whitespace but preserve paragraph breaks
        text = " ".join(text.split())
        if text.strip():
            results.append({
                "text": text,
                "metadata": {
                    "source": filename,
                    "type": "pdf",
                    "page": i
                }
            })

    print(f"  → Extracted {len(results)} pages from {filename}")
    return results
