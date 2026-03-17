import logging
from .base_extractor import BaseExtractor, ExtractionResult, ExtractedPage

logger = logging.getLogger(__name__)


class DocxExtractor(BaseExtractor):
    """Extract text and tables from DOCX files."""

    def extract(self, file_path: str) -> ExtractionResult:
        result = self._make_result(file_path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        try:
            from docx import Document
            doc = Document(file_path)
            # Treat the whole document as one "page" unless page breaks exist
            sections: list[str] = []
            tables: list[list[list[str]]] = []

            for block in doc.element.body:
                tag = block.tag.split("}")[-1] if "}" in block.tag else block.tag
                if tag == "p":
                    from docx.oxml.ns import qn
                    para_text = "".join(
                        run.text for run in block.findall(f".//{qn('w:t')}")
                    )
                    if para_text.strip():
                        sections.append(para_text.strip())
                elif tag == "tbl":
                    table_data = self._extract_table(block)
                    tables.append(table_data)
                    # Also add as text
                    sections.append("\n".join(" | ".join(row) for row in table_data))

            result.pages.append(ExtractedPage(
                page_number=1,
                content="\n".join(sections),
                tables=tables,
                page_type="mixed" if tables else "text",
            ))
            result.metadata["paragraph_count"] = len(doc.paragraphs)
            result.metadata["table_count"] = len(doc.tables)
        except Exception as exc:
            logger.error("DOCX extraction failed for %s: %s", file_path, exc)
            result.error = str(exc)
        return result

    @staticmethod
    def _extract_table(tbl_element) -> list[list[str]]:
        from docx.oxml.ns import qn
        rows = []
        for tr in tbl_element.findall(f".//{qn('w:tr')}"):
            row = []
            for tc in tr.findall(f".//{qn('w:tc')}"):
                cell_text = "".join(
                    t.text or "" for t in tc.findall(f".//{qn('w:t')}")
                )
                row.append(cell_text.strip())
            if row:
                rows.append(row)
        return rows
