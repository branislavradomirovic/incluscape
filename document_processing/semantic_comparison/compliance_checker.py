"""
ComplianceChecker — orchestrates the full pipeline:
  classify → match reference template → compare → persist result.
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ComplianceChecker:
    """
    High-level orchestrator for semantic compliance analysis.

    Usage:
        checker = ComplianceChecker(db)
        result  = checker.analyse(document_id=42, document_text="...")
    """

    def __init__(self, db=None, matcher=None):
        from config import Config
        from database.db_manager import DatabaseManager
        from document_processing.semantic_comparison.category_matcher import CategoryMatcher

        self.db = db or DatabaseManager()
        self.matcher = matcher or CategoryMatcher(db=self.db)
        self._enabled = Config.ENABLE_SEMANTIC_ANALYSIS

    # ------------------------------------------------------------------
    def analyse(
        self,
        document_id: int,
        document_text: str,
        reference_template: Optional[Dict[str, Any]] = None,
        save: bool = True,
        on_progress=None,
    ) -> Dict[str, Any]:
        """
        Run full semantic compliance analysis for a document.

        If `reference_template` is provided it is used directly;
        otherwise auto-classification + matching is run first.

        Returns a merged result dict that is also persisted (if save=True).
        """
        if not self._enabled:
            return {
                "error": "Semantic analysis is disabled. Set ENABLE_SEMANTIC_ANALYSIS=True in .env",
                "compliance_score": None,
            }

        def emit(stage: str, status: str, payload: Optional[Dict[str, Any]] = None):
            if callable(on_progress):
                on_progress(stage, status, payload or {})

        # ── Step 1: classify + match ───────────────────────────────────
        if reference_template is None:
            match_result = self.matcher.classify_and_match(document_text, on_progress=on_progress)
            classification = match_result["classification"]
            templates = match_result["matched_templates"]
            # Pick best match (first one; user can re-run with explicit choice)
            reference_template = templates[0] if templates else None
        else:
            emit("classify", "skipped", {"message": "Skipped auto-classification because a reference template was selected."})
            emit("match", "skipped", {"message": "Skipped automatic template matching because a reference template was selected."})
            classification = {
                "body": reference_template.get("body"),
                "category": reference_template.get("category"),
                "confidence": 1.0,
            }

        # ── Step 2: compliance comparison ─────────────────────────────
        if reference_template:
            emit(
                "compare",
                "running",
                {
                    "template": reference_template.get("name", "Unknown template"),
                    "message": f"Comparing document against {reference_template.get('name', 'selected template')}.",
                },
            )

            compare_stream = None
            if callable(on_progress):
                def compare_stream(part, obj, elapsed, done):
                    payload = {
                        "template": reference_template.get("name", "Unknown template"),
                        "message": "Streaming compliance comparison response.",
                        "part": part,
                        "elapsed": elapsed,
                    }
                    if isinstance(obj, dict):
                        if obj.get("compliance_score") is not None:
                            payload["score"] = obj.get("compliance_score")
                        if obj.get("summary"):
                            payload["message"] = obj.get("summary")
                    on_progress("compare", "running", payload)

            comparison = self.matcher.analyzer.compare_with_template(
                document_text,
                reference_template,
                on_progress=compare_stream,
            )
            emit(
                "compare",
                "completed" if "error" not in comparison else "failed",
                {
                    "template": reference_template.get("name", "Unknown template"),
                    "score": comparison.get("compliance_score"),
                    "message": comparison.get("summary") or comparison.get("error") or "Compliance comparison completed.",
                },
            )
        else:
            comparison = {
                "compliance_score": 0.0,
                "summary": "No matching reference template found.",
                "missing_elements": ["No reference template available for this body/category"],
                "recommendations": ["Add a reference template for this document type"],
            }
            emit("compare", "failed", {"message": "No matching reference template found."})

        # ── Step 3: merge and persist ──────────────────────────────────
        ref_id = reference_template.get("id") if reference_template else None

        row: Dict[str, Any] = {
            "document_id": document_id,
            "reference_template_id": ref_id if isinstance(ref_id, int) else None,
            "model_used": getattr(self.matcher.analyzer, "model_name", "unknown"),
            "body_detected": classification.get("body"),
            "category_detected": classification.get("category"),
            "compliance_score": comparison.get("compliance_score"),
            "present_elements": json.dumps(comparison.get("present_elements", [])),
            "missing_elements": json.dumps(comparison.get("missing_elements", [])),
            "partial_elements": json.dumps(comparison.get("partial_elements", [])),
            "strengths": json.dumps(comparison.get("strengths", [])),
            "gaps": json.dumps(comparison.get("gaps", [])),
            "recommendations": json.dumps(comparison.get("recommendations", [])),
            "summary": comparison.get("summary", ""),
            "full_response_json": json.dumps({
                "classification": classification,
                "comparison": comparison,
            }),
        }

        if "error" in comparison:
            row["error"] = comparison.get("error")

        if save and "error" not in comparison:
            emit("persist", "running", {"message": "Saving semantic analysis result."})
            analysis_id = self.db.save_semantic_analysis(row)
            row["id"] = analysis_id
            logger.info(
                "Semantic analysis saved (id=%d, doc=%d, score=%.2f)",
                analysis_id, document_id, comparison.get("compliance_score", 0),
            )
            emit("persist", "completed", {"analysis_id": analysis_id, "message": "Semantic analysis saved."})
        elif save:
            emit("persist", "skipped", {"message": "Result not saved because the comparison returned an error."})

        # Deserialise JSON arrays for convenience
        for key in ("present_elements", "missing_elements", "partial_elements",
                    "strengths", "gaps", "recommendations"):
            if isinstance(row.get(key), str):
                try:
                    row[key] = json.loads(row[key])
                except (json.JSONDecodeError, TypeError):
                    row[key] = []

        row["reference_template"] = reference_template
        return row

    # ------------------------------------------------------------------
    def get_analyses(self, document_id: int) -> List[Dict]:
        """Retrieve all past analyses for a document, deserialising JSON fields."""
        rows = self.db.get_semantic_analyses(document_id)
        for row in rows:
            for key in ("present_elements", "missing_elements", "partial_elements",
                        "strengths", "gaps", "recommendations"):
                if isinstance(row.get(key), str):
                    try:
                        row[key] = json.loads(row[key])
                    except (json.JSONDecodeError, TypeError):
                        row[key] = []
        return rows
