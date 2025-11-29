"""Text extraction from large PDFs, Word documents, and images.

Strategy for PDFs (the 300-400 page case):
  * Use PyMuPDF (``fitz``) to pull the embedded text layer page by page — this
    is fast even for huge documents and streams one page at a time so memory
    stays flat.
  * When a page has little or no text layer (a scanned page or an image-only
    page), rasterise just that page and run Tesseract OCR on it. We only pay
    the OCR cost for the pages that actually need it.

Everything yields ``Page`` objects so downstream chunking can keep page
numbers for citations.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Iterator

import fitz  # PyMuPDF
import pytesseract
from docx import Document as DocxDocument
from PIL import Image

from app.config import get_settings

settings = get_settings()

if settings.tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd


@dataclass
class Page:
    number: int          # 1-indexed
    text: str
    ocr: bool = False    # whether OCR was used for this page


@dataclass
class ExtractionResult:
    pages: list[Page] = field(default_factory=list)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def ocr_pages(self) -> int:
        return sum(1 for p in self.pages if p.ocr)

    @property
    def char_count(self) -> int:
        return sum(len(p.text) for p in self.pages)


def _ocr_image(image: Image.Image) -> str:
    return pytesseract.image_to_string(image, lang=settings.tesseract_lang)


def _ocr_pdf_page(page: "fitz.Page") -> str:
    """Rasterise a single PDF page and OCR it."""
    zoom = settings.ocr_dpi / 72.0  # 72 dpi is the PDF base resolution
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix)
    image = Image.open(io.BytesIO(pix.tobytes("png")))
    return _ocr_image(image)


def extract_pdf(path: str) -> Iterator[Page]:
    """Yield pages from a PDF, OCR-ing scanned pages on demand."""
    doc = fitz.open(path)
    try:
        for index in range(doc.page_count):
            page = doc.load_page(index)
            text = page.get_text("text").strip()
            used_ocr = False
            if len(text) < settings.ocr_min_text_chars:
                ocr_text = _ocr_pdf_page(page).strip()
                if len(ocr_text) > len(text):
                    text, used_ocr = ocr_text, True
            yield Page(number=index + 1, text=text, ocr=used_ocr)
    finally:
        doc.close()


def extract_docx(path: str) -> Iterator[Page]:
    """Extract text from a .docx file.

    Word documents have no real page concept, so we emit logical "pages" by
    grouping paragraphs, keeping chunk sizes manageable downstream.
    """
    document = DocxDocument(path)
    buffer: list[str] = []
    page_no = 1
    char_budget = 3000

    def flush(num: int, parts: list[str]) -> Page:
        return Page(number=num, text="\n".join(parts).strip(), ocr=False)

    running = 0
    for para in document.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        buffer.append(text)
        running += len(text)
        if running >= char_budget:
            yield flush(page_no, buffer)
            page_no += 1
            buffer, running = [], 0
    if buffer:
        yield flush(page_no, buffer)


def extract_image(path: str) -> Iterator[Page]:
    """OCR a standalone image file."""
    image = Image.open(path)
    text = _ocr_image(image).strip()
    yield Page(number=1, text=text, ocr=True)


# Map a normalised content type / extension to its extractor.
_PDF_TYPES = {"application/pdf"}
_DOCX_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}
_IMAGE_PREFIX = "image/"


def extract(path: str, content_type: str, filename: str) -> ExtractionResult:
    """Dispatch to the right extractor and collect all pages."""
    ct = (content_type or "").lower()
    name = filename.lower()

    if ct in _PDF_TYPES or name.endswith(".pdf"):
        pages = list(extract_pdf(path))
    elif ct in _DOCX_TYPES or name.endswith((".docx", ".doc")):
        pages = list(extract_docx(path))
    elif ct.startswith(_IMAGE_PREFIX) or name.endswith(
        (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp")
    ):
        pages = list(extract_image(path))
    else:
        raise ValueError(f"Unsupported file type: {content_type or filename}")

    return ExtractionResult(pages=pages)
