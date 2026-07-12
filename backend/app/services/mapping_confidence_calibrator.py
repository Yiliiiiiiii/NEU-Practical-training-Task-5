from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CalibrationSample:
    score: float
    correct: bool


class MappingConfidenceCalibrator:
    def __init__(self, artifact: dict[str, Any] | None = None) -> None:
        self.artifact = artifact or {"method": "identity", "bins": []}
        method = self.artifact.get("method", "identity")
        if method not in {"identity", "bin_monotonic"}:
            raise ValueError(f"unsupported calibration method: {method}")

    def calibrate(self, score: float) -> float:
        bounded = max(0.0, min(float(score), 1.0))
        if self.artifact.get("method") == "identity":
            return bounded
        for item in self.artifact.get("bins", []):
            if bounded <= float(item["upper_bound"]):
                return float(item["probability"])
        bins = self.artifact.get("bins", [])
        return float(bins[-1]["probability"]) if bins else bounded

    @classmethod
    def fit(cls, samples: list[CalibrationSample], *, bin_count: int = 10) -> dict[str, Any]:
        if not samples:
            raise ValueError("calibration requires at least one dev sample")
        if bin_count < 2:
            raise ValueError("calibration requires at least two bins")
        grouped: list[dict[str, Any]] = []
        for index in range(bin_count):
            lower = index / bin_count
            upper = (index + 1) / bin_count
            members = [
                sample
                for sample in samples
                if sample.score >= lower and (sample.score < upper or index == bin_count - 1)
            ]
            if not members:
                continue
            grouped.append(
                {
                    "lower_bound": lower,
                    "upper_bound": upper,
                    "count": len(members),
                    "positive_count": sum(sample.correct for sample in members),
                }
            )

        pools = [dict(item) for item in grouped]
        index = 0
        while index < len(pools) - 1:
            left = pools[index]
            right = pools[index + 1]
            left_rate = left["positive_count"] / left["count"]
            right_rate = right["positive_count"] / right["count"]
            if left_rate <= right_rate:
                index += 1
                continue
            merged = {
                "lower_bound": left["lower_bound"],
                "upper_bound": right["upper_bound"],
                "count": left["count"] + right["count"],
                "positive_count": left["positive_count"] + right["positive_count"],
            }
            pools[index : index + 2] = [merged]
            index = max(0, index - 1)

        bins = []
        for pool in pools:
            probability = pool["positive_count"] / pool["count"]
            bins.append(
                {
                    **pool,
                    "lower_bound": round(pool["lower_bound"], 6),
                    "upper_bound": round(pool["upper_bound"], 6),
                    "probability": round(probability, 6),
                }
            )
        artifact = {
            "artifact_version": "1.0.0",
            "method": "bin_monotonic",
            "fit_split": "dev",
            "bins": bins,
        }
        report = cls(artifact).report(samples)
        artifact["brier_score"] = report["brier_score"]
        artifact["expected_calibration_error"] = report["expected_calibration_error"]
        artifact["reliability_bins"] = report["reliability_bins"]
        artifact["precision_coverage_curve"] = report["precision_coverage_curve"]
        return artifact

    def report(self, samples: list[CalibrationSample]) -> dict[str, Any]:
        rows = [
            (self.calibrate(sample.score), 1.0 if sample.correct else 0.0) for sample in samples
        ]
        brier = sum((confidence - outcome) ** 2 for confidence, outcome in rows) / len(rows)
        reliability: list[dict[str, Any]] = []
        for item in self.artifact.get("bins", []):
            members = [
                sample
                for sample in samples
                if sample.score >= float(item["lower_bound"])
                and sample.score <= float(item["upper_bound"])
            ]
            if not members:
                continue
            reliability.append(
                {
                    "lower_bound": item["lower_bound"],
                    "upper_bound": item["upper_bound"],
                    "count": len(members),
                    "mean_confidence": round(
                        sum(self.calibrate(sample.score) for sample in members) / len(members),
                        6,
                    ),
                    "accuracy": round(sum(sample.correct for sample in members) / len(members), 6),
                }
            )
        expected_error = sum(
            abs(item["mean_confidence"] - item["accuracy"]) * item["count"] / len(samples)
            for item in reliability
        )
        curve = []
        for threshold in sorted({confidence for confidence, _ in rows}, reverse=True):
            covered = [outcome for confidence, outcome in rows if confidence >= threshold]
            curve.append(
                {
                    "threshold": round(threshold, 6),
                    "precision": round(sum(covered) / len(covered), 6),
                    "coverage": round(len(covered) / len(rows), 6),
                }
            )
        return {
            "brier_score": round(brier, 6),
            "expected_calibration_error": round(expected_error, 6),
            "reliability_bins": reliability,
            "precision_coverage_curve": curve,
        }
