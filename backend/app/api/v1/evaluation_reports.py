import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas.api import EvaluationReportResponse

router = APIRouter(prefix="/evaluation-reports", tags=["evaluation-reports"])

ROOT = Path(__file__).resolve().parents[4]
REPORTS = {
    "real-world-knowledge-loop": {
        "path": ROOT / "reports" / "real_world_knowledge_loop_report.json",
        "recommended_command": "python scripts/eval_real_world_knowledge_loop.py",
    },
    "chunk-retrieval": {
        "path": ROOT / "reports" / "chunk_retrieval_eval_report.json",
        "recommended_command": "python scripts/eval_chunk_retrieval.py",
    },
    "llm-fallback": {
        "path": ROOT / "reports" / "llm_fallback_eval_report.json",
        "recommended_command": "python scripts/eval_llm_fallback.py",
    },
}


@router.get("/{report_id}", response_model=EvaluationReportResponse)
def get_evaluation_report(report_id: str) -> dict[str, Any]:
    entry = REPORTS.get(report_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="evaluation report not found")

    path = Path(entry["path"])
    if not path.is_file():
        return {
            "status": "unavailable",
            "recommended_command": entry["recommended_command"],
        }
    return {
        "status": "available",
        "report": json.loads(path.read_text(encoding="utf-8")),
    }
