from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class ExtractedPage:
    page_number: int
    content: str
    tables: List[List[List[str]]] = field(default_factory=list)
    page_type: str = "text"  # text | table | image | mixed

    @property
    def word_count(self) -> int:
        return len(self.content.split())


@dataclass
class ExtractionResult:
    file_path: str
    file_name: str
    mime_type: str
    pages: List[ExtractedPage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.content for p in self.pages)

    @property
    def page_count(self) -> int:
        return len(self.pages)


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, file_path: str) -> ExtractionResult:
        """Extract content from a document file."""

    def _make_result(self, file_path: str, mime_type: str) -> ExtractionResult:
        import os
        return ExtractionResult(
            file_path=file_path,
            file_name=os.path.basename(file_path),
            mime_type=mime_type,
        )
