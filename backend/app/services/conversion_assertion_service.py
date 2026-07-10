from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from app.schemas.conversion_assertion_report import (
    ConversionAssertionIssue,
    ConversionAssertionReport,
    ConversionAssertionResult,
)
from app.schemas.conversion_assertions import (
    ConversionAssertionConfig,
    ConversionAssertionDefinition,
)
from app.services.json_path_service import JsonPathService, PathResolution


class ConversionAssertionService:
    def __init__(self, path_service: JsonPathService | None = None) -> None:
        self.path_service = path_service or JsonPathService()

    def evaluate(
        self,
        *,
        task_id: str,
        schema_pack_id: str,
        schema_pack_version: str,
        schema_id: str,
        content_json: dict[str, Any],
        assertion_config: ConversionAssertionConfig,
        mapping_report: dict[str, Any] | None = None,
    ) -> ConversionAssertionReport:
        results: list[ConversionAssertionResult] = []
        issues: list[ConversionAssertionIssue] = []

        for definition in assertion_config.assertions:
            severity = definition.severity or assertion_config.defaults.severity
            resolution = self.path_service.resolve(content_json, definition.path)
            if not resolution.found and definition.optional and resolution.error is None:
                results.append(self._result(definition, severity, "skipped"))
                continue
            if definition.optional and definition.operator in {
                "equal_to_path",
                "not_equal_to_path",
            }:
                other = self.path_service.resolve(
                    content_json,
                    definition.parameters["other_path"],
                )
                if not other.found and other.error is None:
                    results.append(self._result(definition, severity, "skipped"))
                    continue

            passed, expected = self._evaluate_operator(
                content_json,
                definition,
                resolution,
            )
            status = "passed" if passed else "failed"
            results.append(self._result(definition, severity, status))
            if not passed:
                evidence = self._mapping_evidence(definition.path, mapping_report)
                issues.append(
                    ConversionAssertionIssue(
                        assertion_id=definition.assertion_id,
                        severity=severity,
                        path=definition.path,
                        operator=definition.operator,
                        message=definition.message
                        or f"Conversion output assertion {definition.assertion_id} failed.",
                        expected=expected,
                        actual_preview=(
                            self._bounded_preview(resolution.value)
                            if resolution.found
                            else None
                        ),
                        **evidence,
                    )
                )

        issues.sort(
            key=lambda item: (
                0 if item.severity == "error" else 1,
                item.assertion_id,
                item.path,
            )
        )
        passed_count = sum(item.status == "passed" for item in results)
        failed_count = sum(item.status == "failed" for item in results)
        skipped_count = sum(item.status == "skipped" for item in results)
        error_count = sum(item.severity == "error" for item in issues)
        warning_count = sum(item.severity == "warning" for item in issues)
        return ConversionAssertionReport(
            task_id=task_id,
            schema_pack_id=schema_pack_id,
            schema_pack_version=schema_pack_version,
            schema_id=schema_id,
            assertion_set_version=assertion_config.assertion_set_version,
            passed=error_count == 0,
            total_count=len(results),
            passed_count=passed_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            error_count=error_count,
            warning_count=warning_count,
            results=results,
            issues=issues,
            generated_at=datetime.now(UTC).isoformat(),
        )

    @staticmethod
    def _result(
        definition: ConversionAssertionDefinition,
        severity: str,
        status: str,
    ) -> ConversionAssertionResult:
        return ConversionAssertionResult(
            assertion_id=definition.assertion_id,
            status=status,
            severity=severity,
            path=definition.path,
            operator=definition.operator,
        )

    def _evaluate_operator(
        self,
        content_json: dict[str, Any],
        definition: ConversionAssertionDefinition,
        resolution: PathResolution,
    ) -> tuple[bool, Any]:
        if resolution.error is not None:
            return False, "valid JSON path"
        if not resolution.found:
            return False, "path exists"

        value = resolution.value
        parameters = definition.parameters
        operator = definition.operator
        if operator == "exists":
            return True, "path exists"
        if operator == "non_empty":
            empty_collection = isinstance(value, list | dict) and len(value) == 0
            empty_string = isinstance(value, str) and not value.strip()
            passed = value is not None and not (
                empty_collection or empty_string
            )
            return passed, "non-empty value"
        if operator == "type_is":
            return self._type_matches(value, parameters["expected"]), parameters["expected"]
        if operator in {"date_format", "datetime_format"}:
            formats = parameters["formats"]
            return self._matches_datetime_format(value, formats), {"formats": formats}
        if operator == "regex_match":
            pattern = re.compile(parameters["pattern"])
            mode = parameters.get("mode", "search")
            matcher = getattr(pattern, mode)
            return isinstance(value, str) and matcher(value) is not None, parameters
        if operator == "enum_allowed":
            return value in parameters["values"], {"values": parameters["values"]}
        if operator == "number_range":
            return self._number_in_range(value, parameters), parameters
        if operator == "text_length":
            return self._length_in_range(value, parameters, str), parameters
        if operator == "array_length":
            return self._length_in_range(value, parameters, list), parameters
        if operator == "url_like":
            parsed = urlparse(value) if isinstance(value, str) else None
            passed = bool(parsed and parsed.scheme in {"http", "https"} and parsed.netloc)
            return passed, {"schemes": ["http", "https"]}
        if operator in {"equal_to_path", "not_equal_to_path"}:
            other = self.path_service.resolve(content_json, parameters["other_path"])
            if not other.found or other.error is not None:
                return False, {"other_path": parameters["other_path"], "resolved": True}
            equal = value == other.value
            return (equal if operator == "equal_to_path" else not equal), parameters
        raise ValueError(f"unsupported assertion operator: {operator}")

    @staticmethod
    def _type_matches(value: Any, expected: str) -> bool:
        if expected == "null":
            return value is None
        if expected == "boolean":
            return isinstance(value, bool)
        if expected == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if expected == "number":
            return isinstance(value, int | float) and not isinstance(value, bool)
        expected_types = {"string": str, "array": list, "object": dict}
        return isinstance(value, expected_types[expected])

    @staticmethod
    def _matches_datetime_format(value: Any, formats: list[str]) -> bool:
        if not isinstance(value, str):
            return False
        for date_format in formats:
            try:
                datetime.strptime(value, date_format)
            except ValueError:
                continue
            return True
        return False

    @staticmethod
    def _number_in_range(value: Any, parameters: dict[str, Any]) -> bool:
        if not isinstance(value, int | float) or isinstance(value, bool):
            return False
        minimum = parameters.get("min")
        maximum = parameters.get("max")
        if minimum is not None:
            if parameters.get("inclusive_min", True) and value < minimum:
                return False
            if not parameters.get("inclusive_min", True) and value <= minimum:
                return False
        if maximum is not None:
            if parameters.get("inclusive_max", True) and value > maximum:
                return False
            if not parameters.get("inclusive_max", True) and value >= maximum:
                return False
        return True

    @staticmethod
    def _length_in_range(
        value: Any,
        parameters: dict[str, Any],
        expected_type: type,
    ) -> bool:
        if not isinstance(value, expected_type):
            return False
        length = len(value)
        return (
            ("min" not in parameters or length >= parameters["min"])
            and ("max" not in parameters or length <= parameters["max"])
        )

    @staticmethod
    def _mapping_evidence(
        path: str,
        mapping_report: dict[str, Any] | None,
    ) -> dict[str, str | None]:
        empty = {
            "source_path": None,
            "source_candidate_id": None,
            "mapping_method": None,
        }
        if not mapping_report or not path.startswith("$.data."):
            return empty
        target_field_id = path.removeprefix("$.data.").split(".", 1)[0].split("[", 1)[0]
        for collection in ("mappings", "review_required_items"):
            items = mapping_report.get(collection, [])
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict) or item.get("target_field_id") != target_field_id:
                    continue
                source = item.get("source_field")
                source = source if isinstance(source, dict) else {}
                return {
                    "source_path": item.get("source_path") or source.get("source_path"),
                    "source_candidate_id": item.get("candidate_id"),
                    "mapping_method": item.get("method") or item.get("strategy"),
                }
        return empty

    @classmethod
    def _bounded_preview(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value[:200]
        if isinstance(value, list):
            return value[:5]
        if isinstance(value, dict):
            keys = list(value)[:10]
            return {"keys": keys, "total_keys": len(value)}
        return value
