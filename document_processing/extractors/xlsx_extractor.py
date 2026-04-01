import logging
from .base_extractor import BaseExtractor, ExtractionResult, ExtractedPage

logger = logging.getLogger(__name__)


class XLSXExtractor(BaseExtractor):
    """Extract data from XLSX/XLS spreadsheets."""

    def extract(self, file_path: str) -> ExtractionResult:
        result = self._make_result(
            file_path,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        try:
            import openpyxl
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            result.metadata["sheet_names"] = wb.sheetnames
            for page_num, sheet_name in enumerate(wb.sheetnames, start=1):
                ws = wb[sheet_name]
                rows: list[list[str]] = []
                for row in ws.iter_rows(values_only=True):
                    cleaned = [str(cell) if cell is not None else "" for cell in row]
                    if any(c.strip() for c in cleaned):
                        rows.append(cleaned)
                table = rows
                text = f"[Sheet: {sheet_name}]\n"
                text += "\n".join(" | ".join(r) for r in rows)
                result.pages.append(ExtractedPage(
                    page_number=page_num,
                    content=text,
                    tables=[table],
                    page_type="table",
                ))
            wb.close()
        except Exception as exc:
            logger.error("XLSX extraction failed for %s: %s", file_path, exc)
            result.error = str(exc)
        return result
