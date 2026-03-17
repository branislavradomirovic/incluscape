import io
import logging
from typing import List

from .base_extractor import BaseExtractor, ExtractionResult, ExtractedPage

logger = logging.getLogger(__name__)


class PDFExtractor(BaseExtractor):
    """Extract text (and optionally OCR images) from PDF files."""

    def __init__(self, enable_ocr: bool = False, ocr_language: str = "eng"):
        self.enable_ocr = enable_ocr
        self.ocr_language = ocr_language

    def extract(self, file_path: str) -> ExtractionResult:
        result = self._make_result(file_path, "application/pdf")
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            result.metadata = dict(reader.metadata or {})
            for i, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                if not text.strip() and self.enable_ocr:
                    text = self._ocr_page(page)
                result.pages.append(ExtractedPage(
                    page_number=i,
                    content=text.strip(),
                    page_type="text" if text.strip() else "image",
                ))
        except Exception as exc:
            logger.error("PDF extraction failed for %s: %s", file_path, exc)
            result.error = str(exc)
        return result

    def _ocr_page(self, page) -> str:
        try:
            import pytesseract
            from PIL import Image
            from config import Config
            for image_file in page.images:
                img = Image.open(io.BytesIO(image_file.data))
                return pytesseract.image_to_string(img, lang=Config.OCR_LANGUAGE)
        except Exception as exc:
            logger.warning("OCR failed: %s", exc)
        return ""
