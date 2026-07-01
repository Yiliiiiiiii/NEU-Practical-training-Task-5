"""Shared helpers for topic 5 real-world evaluation scripts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} must contain a JSON object")
            rows.append(value)
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_markdown(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def safe_ratio(numerator: int | float, denominator: int | float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def _source_name(item: dict[str, Any]) -> str | None:
    source_field = item.get("source_field")
    if isinstance(source_field, dict):
        value = source_field.get("source_name")
        if isinstance(value, str) and value:
            return value
    value = item.get("source_name")
    return value if isinstance(value, str) and value else None


def _source_path(item: dict[str, Any]) -> str | None:
    source_field = item.get("source_field")
    if isinstance(source_field, dict):
        value = source_field.get("source_path")
        if isinstance(value, str) and value:
            return value
    value = item.get("source_path")
    return value if isinstance(value, str) and value else None


def _target_field(item: dict[str, Any]) -> str | None:
    for key in ("target_field_id", "target_field", "field_id"):
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _source_key(
    item: dict[str, Any],
    target_field: str | None = None,
) -> tuple[str, str, str] | None:
    target = target_field or _target_field(item)
    if not target:
        return None
    source_name = _source_name(item)
    if source_name:
        return ("name", source_name, target)
    source_path = _source_path(item)
    if source_path:
        return ("path", source_path, target)
    return None


def _target_candidates(item: dict[str, Any]) -> set[str]:
    candidates = item.get("target_field_candidates")
    if isinstance(candidates, list):
        return {candidate for candidate in candidates if isinstance(candidate, str)}
    target = _target_field(item)
    return {target} if target else set()


def _accepted_mappings(mapping_report: dict[str, Any]) -> list[dict[str, Any]]:
    mappings = mapping_report.get("mappings", [])
    if not isinstance(mappings, list):
        return []
    return [
        item
        for item in mappings
        if isinstance(item, dict) and item.get("status", "accepted") == "accepted"
    ]


def _review_required_items(mapping_report: dict[str, Any]) -> list[dict[str, Any]]:
    items = mapping_report.get("review_required_items", [])
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _key_matches(expected: dict[str, Any], actual: dict[str, Any], target: str) -> bool:
    expected_name = _source_name(expected)
    actual_name = _source_name(actual)
    if expected_name and actual_name:
        return expected_name == actual_name and _target_field(actual) == target
    expected_path = _source_path(expected)
    actual_path = _source_path(actual)
    return bool(
        expected_path
        and actual_path
        and expected_path == actual_path
        and _target_field(actual) == target
    )


def _matches_review(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    expected_name = _source_name(expected)
    actual_name = _source_name(actual)
    expected_path = _source_path(expected)
    actual_path = _source_path(actual)
    source_matches = bool(
        expected_name and actual_name and expected_name == actual_name
    ) or bool(expected_path and actual_path and expected_path == actual_path)
    if not source_matches:
        return False
    expected_targets = _target_candidates(expected)
    actual_targets = _target_candidates(actual)
    return not expected_targets or bool(expected_targets & actual_targets)


def _forbidden_mapping(badcase: dict[str, Any]) -> dict[str, Any] | None:
    forbidden = badcase.get("forbidden_auto_mapping")
    if isinstance(forbidden, dict):
        return forbidden
    source_name = badcase.get("source_name")
    target = badcase.get("forbidden_target_field")
    if isinstance(source_name, str) and isinstance(target, str):
        return {"source_name": source_name, "target_field": target}
    return None


def score_mapping_report(
    gold: dict[str, Any],
    mapping_report: dict[str, Any],
) -> dict[str, Any]:
    accepted = _accepted_mappings(mapping_report)
    review_items = _review_required_items(mapping_report)
    expected_mappings = [
        item for item in gold.get("expected_mappings", []) if isinstance(item, dict)
    ]
    expected_reviews = [
        item
        for item in gold.get("expected_review_required", [])
        if isinstance(item, dict)
    ]

    accepted_correct = 0
    matched_expected_mapping_indexes: set[int] = set()
    for index, expected in enumerate(expected_mappings):
        target = _target_field(expected)
        if target and any(
            _key_matches(expected, actual, target) for actual in accepted
        ):
            accepted_correct += 1
            matched_expected_mapping_indexes.add(index)

    review_correct = 0
    for expected in expected_reviews:
        if any(_matches_review(expected, actual) for actual in review_items):
            review_correct += 1

    missing_gold_mappings = len(expected_mappings) - len(
        matched_expected_mapping_indexes
    )
    badcase_violations: list[dict[str, Any]] = []
    for badcase in gold.get("known_badcases", []):
        if not isinstance(badcase, dict):
            continue
        forbidden = _forbidden_mapping(badcase)
        if forbidden is None:
            continue
        forbidden_target = _target_field(forbidden)
        if forbidden_target is None:
            continue
        for actual in accepted:
            if _key_matches(forbidden, actual, forbidden_target):
                badcase_violations.append(
                    {
                        "case_id": badcase.get("case_id"),
                        "source_name": _source_name(forbidden),
                        "source_path": _source_path(forbidden),
                        "target_field": forbidden_target,
                    }
                )
                break

    gold_signal_count = len(expected_mappings) + len(expected_reviews)
    return {
        "doc_id": gold.get("doc_id"),
        "gold_mapping_count": len(expected_mappings),
        "gold_review_required_count": len(expected_reviews),
        "auto_accepted_correct": accepted_correct,
        "review_required_correct": review_correct,
        "missing_gold_mappings": missing_gold_mappings,
        "badcase_violation_count": len(badcase_violations),
        "badcase_violations": badcase_violations,
        "mapping_recall": safe_ratio(
            accepted_correct + review_correct, gold_signal_count
        ),
    }


def aggregate_mapping_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {
        "document_count": len(rows),
        "gold_mapping_count": 0,
        "gold_review_required_count": 0,
        "auto_accepted_correct": 0,
        "review_required_correct": 0,
        "missing_gold_mappings": 0,
        "badcase_violation_count": 0,
    }
    for row in rows:
        for key in (
            "gold_mapping_count",
            "gold_review_required_count",
            "auto_accepted_correct",
            "review_required_correct",
            "missing_gold_mappings",
            "badcase_violation_count",
        ):
            value = row.get(key, 0)
            if isinstance(value, int | float):
                totals[key] += value
    denominator = totals["gold_mapping_count"] + totals["gold_review_required_count"]
    totals["mapping_recall"] = safe_ratio(
        totals["auto_accepted_correct"] + totals["review_required_correct"],
        denominator,
    )
    totals["badcase_pass_rate"] = 1.0 if totals["badcase_violation_count"] == 0 else 0.0
    return totals


class EvaluationHttpClient:
    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        headers = {"X-API-Key": api_key} if api_key else None
        self.client = client or httpx.Client(
            base_url=base_url,
            headers=headers,
            timeout=timeout,
        )

    @staticmethod
    def _json_response(response: httpx.Response) -> dict[str, Any]:
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("API response must be a JSON object")
        return data

    def import_document(self, uir: dict[str, Any]) -> dict[str, Any]:
        return self._json_response(
            self.client.post("/api/v1/documents/import", json={"uir": uir})
        )

    def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._json_response(self.client.post("/api/v1/tasks", json=payload))

    def execute_task(self, task_id: str) -> dict[str, Any]:
        return self._json_response(self.client.post(f"/api/v1/tasks/{task_id}/execute"))

    def report(self, task_id: str, report_name: str) -> dict[str, Any]:
        return self._json_response(
            self.client.get(f"/api/v1/tasks/{task_id}/reports/{report_name}")
        )

    def package(self, task_id: str) -> dict[str, Any]:
        return self._json_response(self.client.get(f"/api/v1/tasks/{task_id}/package"))

    def list_reviews(self, status: str) -> list[dict[str, Any]]:
        data = self._json_response(
            self.client.get("/api/v1/reviews", params={"status": status})
        )
        items = data.get("items", [])
        return items if isinstance(items, list) else []

    def approve_review(self, review_id: str) -> dict[str, Any]:
        return self._json_response(
            self.client.post(
                f"/api/v1/reviews/{review_id}/approve",
                json={
                    "reviewer": "topic5_eval",
                    "comment": "Approved for topic 5 knowledge-loop evaluation.",
                    "create_knowledge_candidate": True,
                },
            )
        )

    def list_candidates(self) -> list[dict[str, Any]]:
        data = self._json_response(self.client.get("/api/v1/knowledge/candidates"))
        items = data.get("items", [])
        return items if isinstance(items, list) else []

    def accept_candidate(self, candidate_id: str) -> dict[str, Any]:
        return self._json_response(
            self.client.post(f"/api/v1/knowledge/candidates/{candidate_id}/accept")
        )

    def create_pack(self, schema_id: str, template_id: str) -> dict[str, Any]:
        return self._json_response(
            self.client.post(
                "/api/v1/knowledge/packs",
                json={
                    "schema_id": schema_id,
                    "template_id": template_id,
                    "name": f"{schema_id} {template_id} topic 5 eval pack",
                    "created_by": "topic5_eval",
                },
            )
        )

    def activate_pack(self, pack_id: str) -> dict[str, Any]:
        return self._json_response(
            self.client.post(f"/api/v1/knowledge/packs/{pack_id}/activate")
        )

    def effective_template(self, schema_id: str, template_id: str) -> dict[str, Any]:
        return self._json_response(
            self.client.get(
                "/api/v1/knowledge/effective-template",
                params={"schema_id": schema_id, "template_id": template_id},
            )
        )

    def knowledge_metrics(self) -> dict[str, Any]:
        return self._json_response(self.client.get("/api/v1/knowledge/metrics"))
