import re
import logging

logger = logging.getLogger(__name__)

# Common noise patterns in extracted text
_WHITESPACE_RE = re.compile(r"\s{2,}")
_BULLET_RE = re.compile(r"^[\u2022\u2023\u25e6\u2043\-\*]\s+", re.MULTILINE)
_PAGE_BREAK_RE = re.compile(r"\f")


class TextCleaner:
    """Clean and normalise raw extracted text."""

    def clean(self, text: str) -> str:
        text = _PAGE_BREAK_RE.sub("\n\n", text)
        text = _BULLET_RE.sub("", text)
        text = _WHITESPACE_RE.sub(" ", text)
        return text.strip()

    def split_sentences(self, text: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]
