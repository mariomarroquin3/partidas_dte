import pdfplumber
from pathlib import Path


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Devuelve todo el texto del PDF concatenado (usado por finder).
    """
    return "\n".join(extract_pages_text(pdf_path))


def extract_pages_text(pdf_path: Path) -> list[str]:
    """
    Devuelve una lista con el texto de cada página del PDF.
    Índice 0 → página 1, índice 1 → página 2, etc.
    """
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            pages.append(text or "")
    return pages
