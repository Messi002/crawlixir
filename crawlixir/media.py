"""Pulls text out of PDFs, Word docs, and images."""

import os


def extract_pdf(file_path):
    """Extract text from a PDF file."""
    import pdfplumber

    text = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
    return "\n\n".join(text)


def extract_docx(file_path):
    """Extract text from a DOCX file."""
    from docx import Document

    doc = Document(file_path)
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_image(file_path):
    """Extract text from an image using OCR (pytesseract)."""
    import pytesseract
    from PIL import Image

    img = Image.open(file_path)
    return pytesseract.image_to_string(img)


def extract(file_path):
    """Auto-detect file type and extract text."""
    ext = os.path.splitext(file_path)[1].lower()
    extractors = {
        ".pdf": extract_pdf,
        ".docx": extract_docx,
        ".png": extract_image,
        ".jpg": extract_image,
        ".jpeg": extract_image,
        ".tiff": extract_image,
        ".bmp": extract_image,
    }
    if ext not in extractors:
        raise ValueError(f"Unsupported file type: {ext}")
    return extractors[ext](file_path)
