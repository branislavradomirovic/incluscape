import json
import sys
import time
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.db_manager import DatabaseManager
from document_processing.semantic_comparison.category_matcher import CategoryMatcher
from document_processing.semantic_comparison.compliance_checker import ComplianceChecker


def _json_ready(value):
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_ready(v) for v in value]
    if isinstance(value, tuple):
        return [_json_ready(v) for v in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def _write_output(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(_json_ready(payload)), encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    if len(sys.argv) != 3:
        return 2

    payload_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    try:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        document_id = int(payload["document_id"])
        reference_template = payload.get("reference_template")

        db = DatabaseManager()
        db.initialize()

        matcher = CategoryMatcher(db=db)
        matcher.seed_database()
        checker = ComplianceChecker(db=db, matcher=matcher)

        pages = db.fetchall(
            "SELECT content FROM document_pages WHERE document_id = ? ORDER BY page_number",
            (document_id,),
        )
        document_text = "\n".join(p["content"] for p in pages if p.get("content"))

        if not document_text.strip():
            _write_output(output_path, {
                "ok": False,
                "error": "No extracted text found for this document. Re-process it first.",
            })
            return 0

        started = time.time()
        result = checker.analyse(
            document_id=document_id,
            document_text=document_text,
            reference_template=reference_template,
        )
        _write_output(output_path, {
            "ok": "error" not in result,
            "result": _json_ready(result),
            "elapsed_sec": round(time.time() - started, 2),
        })
        return 0
    except Exception as exc:
        _write_output(output_path, {
            "ok": False,
            "error": str(exc),
        })
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
