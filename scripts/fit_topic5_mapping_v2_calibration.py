"""Fit and freeze Topic 5 mapping-v2 confidence calibration from dev only."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
SCRIPTS = ROOT / "scripts"
DEFAULT_DATASET = ROOT / "eval" / "topic5_mapping_v2"
DEFAULT_OUTPUT = ROOT / "eval" / "topic5_mapping_engine_v2" / "calibration.json"

for path in (BACKEND, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import eval_topic5_mapping_v2 as benchmark  # noqa: E402
from app.schemas.mapping_template import MappingTemplate  # noqa: E402
from app.schemas.target_schema import TargetSchema  # noqa: E402
from app.schemas.uir import UIRDocument  # noqa: E402
from app.services.candidate_service import CandidateService  # noqa: E402
from app.services.mapping_confidence_calibrator import (  # noqa: E402
    CalibrationSample,
    MappingConfidenceCalibrator,
)
from app.services.mapping_service import MappingService  # noqa: E402


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect_dev_samples(
    dataset: benchmark.MappingV2Dataset,
) -> tuple[list[CalibrationSample], int]:
    manifest = {str(row["doc_id"]): row for row in dataset.manifest}
    negatives_by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in dataset.negative_pairs:
        negatives_by_doc[str(row["doc_id"])].append(row)
    gold_keys = {
        (str(row["doc_id"]), str(row["source_path"]), str(row["target_field_id"]))
        for row in dataset.gold["dev"]
    }
    samples: list[CalibrationSample] = []
    for doc_id in dataset.splits["dev"]:
        schema_id = str(manifest[doc_id]["schema_id"])
        uir = UIRDocument.model_validate(dataset.uirs[doc_id])
        candidates = CandidateService().extract_candidates(
            doc_id, uir, enable_legacy_domain_rules=False
        )
        report = MappingService().map_fields(
            doc_id,
            uir,
            TargetSchema.model_validate(dataset.schemas[schema_id]),
            MappingTemplate.model_validate(dataset.rules[schema_id]),
            candidates,
            {
                "mapping_mode": "global_assignment",
                "auto_accept_threshold": 0.0,
                "review_threshold": 0.0,
                "min_candidate_score": 0.0,
                "negative_pairs": negatives_by_doc[doc_id],
                "enable_llm_fallback": False,
            },
        )
        for mapping in report.mappings:
            key = (
                doc_id,
                str(mapping["source_path"]),
                str(mapping["target_field_id"]),
            )
            samples.append(
                CalibrationSample(
                    score=float(mapping["ranking_trace"]["final_score"]),
                    correct=key in gold_keys,
                )
            )
    return samples, len(gold_keys)


def freeze_thresholds(
    samples: list[CalibrationSample],
    calibrator: MappingConfidenceCalibrator,
    *,
    positive_count: int,
) -> dict[str, float]:
    rows = [(calibrator.calibrate(sample.score), sample.correct) for sample in samples]
    eligible: list[tuple[float, float]] = []
    for threshold in sorted({confidence for confidence, _ in rows}, reverse=True):
        accepted = [correct for confidence, correct in rows if confidence >= threshold]
        precision = sum(accepted) / len(accepted)
        recall = sum(accepted) / positive_count
        if precision >= 0.90 and recall >= 0.85:
            eligible.append((recall, threshold))
    if not eligible:
        raise ValueError("dev split cannot satisfy mapping precision/recall targets")
    auto_accept = max(eligible)[1]
    rejected_confidences = [
        confidence
        for confidence, correct in rows
        if not correct and confidence < auto_accept
    ]
    rejected_max = max(rejected_confidences, default=0.0)
    review_required = round((auto_accept + rejected_max) / 2.0, 6)
    return {
        "auto_accept": round(auto_accept, 6),
        "review_required": review_required,
    }


ENGINE_SOURCE_FILES = (
    "backend/app/services/candidate_service.py",
    "backend/app/services/field_descriptor_service.py",
    "backend/app/services/global_assignment_mapping_service.py",
    "backend/app/services/global_assignment_solver.py",
    "backend/app/services/mapping_confidence_calibrator.py",
    "backend/app/services/mapping_constraint_service.py",
    "backend/app/services/mapping_pair_feature_service.py",
)


def _engine_source_sha256() -> str:
    rows = []
    for name in ENGINE_SOURCE_FILES:
        normalized = (ROOT / name).read_text(encoding="utf-8").encode()
        rows.append(f"{name}:{hashlib.sha256(normalized).hexdigest()}")
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()


def build_artifact(
    dataset_root: Path, *, engine_commit: str | None = None
) -> dict[str, Any]:
    dataset = benchmark.load_dataset(dataset_root)
    benchmark.validate_dataset(dataset)
    samples, positive_count = collect_dev_samples(dataset)
    artifact = MappingConfidenceCalibrator.fit(samples, bin_count=10)
    calibrator = MappingConfidenceCalibrator(artifact)
    artifact.update(
        {
            "dataset_id": dataset.hashes["dataset_id"],
            "dataset_version": dataset.hashes["version"],
            "dataset_sha256": dataset.hashes["dataset_sha256"],
            "fit_engine_commit": engine_commit or _git_head(),
            "fit_engine_source_sha256": _engine_source_sha256(),
            "fit_sample_count": len(samples),
            "fit_positive_count": sum(sample.correct for sample in samples),
            "dev_gold_positive_count": positive_count,
            "dev_gold_sha256": _sha256(dataset_root / "gold" / "dev.jsonl"),
            "thresholds": freeze_thresholds(
                samples, calibrator, positive_count=positive_count
            ),
            "claim_boundary": "frozen_public_dev_calibration_only",
            "test_labels_used_for_fit": False,
        }
    )
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--engine-commit")
    args = parser.parse_args()
    artifact = build_artifact(
        args.dataset.resolve(), engine_commit=args.engine_commit
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(artifact, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
