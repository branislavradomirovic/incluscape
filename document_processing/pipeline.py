import hashlib
import logging
from pathlib import Path
from typing import Optional

from .extractors import (
    BaseExtractor, ExtractionResult,
    PDFExtractor, DocxExtractor, XLSXExtractor,
)
from .processors.text_cleaner import TextCleaner
from .processors.entity_recognizer import EntityRecognizer

logger = logging.getLogger(__name__)

_EXTRACTORS: dict[str, type[BaseExtractor]] = {
    ".pdf":  PDFExtractor,
    ".docx": DocxExtractor,
    ".doc":  DocxExtractor,
    ".xlsx": XLSXExtractor,
    ".xls":  XLSXExtractor,
}


class DocumentProcessingPipeline:
    """Orchestrate extraction → cleaning → entity recognition for a single file."""

    def __init__(self, enable_ocr: bool = False):
        self.cleaner = TextCleaner()
        self.recognizer = EntityRecognizer()
        self.enable_ocr = enable_ocr

    # ------------------------------------------------------------------
    def process(self, file_path: str, document_id: int = 0) -> dict:
        """
        Process a document file end-to-end.

        Returns a dict with keys:
            result      ExtractionResult
            entities    list[dict]
            file_hash   str
            error       str | None
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        extractor_cls = _EXTRACTORS.get(suffix)
        if extractor_cls is None:
            return {
                "result": None,
                "entities": [],
                "file_hash": "",
                "error": f"Unsupported file type: {suffix}",
            }

        # Instantiate with OCR setting for PDF
        extractor = (
            extractor_cls(enable_ocr=self.enable_ocr)
            if suffix == ".pdf"
            else extractor_cls()
        )

        file_hash = self._hash_file(file_path)
        result: ExtractionResult = extractor.extract(file_path)

        # Clean text in-place
        for page in result.pages:
            page.content = self.cleaner.clean(page.content)

        # Entity recognition
        entities = []
        for page in result.pages:
            if page.content:
                ents = self.recognizer.recognize(
                    page.content,
                    document_id=document_id,
                    page_number=page.page_number,
                )
                entities.extend(ents)

        return {
            "result": result,
            "entities": entities,
            "file_hash": file_hash,
            "error": result.error,
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _hash_file(file_path: str) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
