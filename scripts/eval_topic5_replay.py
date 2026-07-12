"""Evaluate deterministic Topic 5 replay and explicit difference reporting."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.config import Settings  # noqa: E402
from app.schemas.topic5_convert import Topic5ConvertRequest  # noqa: E402
from app.schemas.topic5_execution import Topic5ExecutionOptions  # noqa: E402
from app.services.conversion_fingerprint_service import (  # noqa: E402
    ConversionFingerprintService,
)
from app.services.topic5_conversion_engine import (  # noqa: E402
    ConversionEngineContext,
    Topic5ConversionEngine,
)

DEFAULT_OUTPUT = ROOT / "eval" / "topic5_replay" / "v1" / "report.json"


def _replay_module():
    path = ROOT / "scripts" / "replay_topic5_snapshot.py"
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load replay implementation")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def run_evaluation(*, commit_sha: str | None = None) -> dict[str, Any]:
    request_path = (
        ROOT
        / "examples"
        / "topic5_inline"
        / "announcement_convert_request.json"
    )
    request = Topic5ConvertRequest.model_validate(
        json.loads(request_path.read_text(encoding="utf-8"))
    )
    result = Topic5ConversionEngine().convert(
        uir=request.uir,
        target_schema=request.target_schema,
        metadata_template=request.metadata_template,
        mapping_rules=request.effective_mapping_template,
        content_organization=request.content_organization,
        execution_options=Topic5ExecutionOptions(
            mapping_mode="legacy", enable_llm_fallback=False
        ),
        output_assertions=request.output_assertions,
        engine_context=ConversionEngineContext(
            task_id="replay-eval-source",
            doc_id=request.uir.doc_id,
            input_mode="inline_topic5_config",
            mapping_input_name="mapping_rules",
            settings=Settings(),
        ),
    )
    replay = _replay_module()
    exact = replay.replay(result.execution_snapshot)
    changed_schema = json.loads(
        json.dumps(result.execution_snapshot["replay_contract"]["target_schema"])
    )
    changed_schema["version"] = "1.0.1"
    schema_diff = replay.replay(
        result.execution_snapshot, target_schema_override=changed_schema
    )
    engine_diff = replay.replay(
        result.execution_snapshot,
        compare_engine_version="topic5-conversion-engine/next",
    )
    cases = [
        {
            "case_id": "same_snapshot_same_engine",
            "passed": exact["status"] == "exact_match"
            and exact["semantic_match"] is True,
            "result": exact,
        },
        {
            "case_id": "changed_schema_version",
            "passed": schema_diff["status"] == "different"
            and "target_schema_hash" in schema_diff["conversion_differences"],
            "result": schema_diff,
        },
        {
            "case_id": "changed_engine_version",
            "passed": engine_diff["status"] == "different"
            and engine_diff["engine_version_match"] is False,
            "result": engine_diff,
        },
    ]
    dataset_sha = hashlib.sha256(request_path.read_bytes()).hexdigest()
    passed_count = sum(case["passed"] for case in cases)
    return {
        "status": "passed" if passed_count == len(cases) else "failed",
        "dataset_id": "topic5_replay",
        "dataset_version": "1.0.0",
        "dataset_sha256": dataset_sha,
        "commit_sha": commit_sha or _git_head(),
        "engine_version": ConversionFingerprintService.ENGINE_VERSION,
        "case_count": len(cases),
        "passed_count": passed_count,
        "replay_semantic_match_rate": 1.0 if exact["semantic_match"] else 0.0,
        "version_difference_detection_rate": (
            sum(case["passed"] for case in cases[1:]) / 2
        ),
        "failed_cases": [case for case in cases if not case["passed"]],
        "cases": cases,
        "reproduction_command": "python scripts/eval_topic5_replay.py",
        "claim_boundary": "Topic 5 snapshot replay only; no scheduler or package mutation",
    }


def main() -> int:
    report = run_evaluation()
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
