import re
from datetime import date, datetime

from app.schemas.metadata_template import MetadataTemplateIssue
from app.schemas.reports import ReportIssue, ValidationReport
from app.schemas.target_schema import TargetField, TargetSchema
from app.services.render_service import RenderedArtifacts
from app.services.transform_service import TransformService


class ValidationService:
    def validate(
        self,
        task_id: str,
        schema: TargetSchema,
        rendered: RenderedArtifacts,
        require_content_organization: bool = False,
        metadata_issues: list[MetadataTemplateIssue] | None = None,
    ) -> ValidationReport:
        issues = [
            ReportIssue(
                level="error",
                message=issue.message,
                stage=issue.stage,
                field_id=issue.field_id,
                path=issue.path,
                code=issue.error_code,
                failure_type="metadata_template",
            )
            for issue in metadata_issues or []
        ]
        data = rendered.structured_json.get("data", {})
        fields_by_id = {field.field_id: field for field in schema.fields}

        for field in schema.fields:
            if field.required and field.field_id not in data:
                issues.append(
                    ReportIssue(
                        level="error",
                        message="Required field is missing.",
                        stage="schema_validation",
                        field_id=field.field_id,
                        path=f"data.{field.field_id}",
                        code="required_field_missing",
                        failure_type="missing_required",
                    )
                )
                continue
            if field.field_id in data:
                issues.extend(
                    self._validate_field(
                        field, data[field.field_id], path=f"data.{field.field_id}"
                    )
                )

        if schema.json_schema.get("additionalProperties") is False:
            for field_id in data.keys() - fields_by_id.keys():
                issues.append(
                    ReportIssue(
                        level="error",
                        message="Unexpected field is forbidden by the target schema.",
                        stage="schema_validation",
                        path=f"data.{field_id}",
                        code="unexpected_field",
                        failure_type="unexpected_field",
                    )
                )

        block_ids = {
            block.get("block_id")
            for block in rendered.structured_json.get("blocks", [])
            if isinstance(block, dict)
        }
        if not rendered.markdown.strip():
            issues.append(
                ReportIssue(level="error", message="Markdown is empty.", code="markdown_empty")
            )
        if not rendered.chunks:
            issues.append(
                ReportIssue(level="error", message="Chunks are empty.", code="chunks_empty")
            )
        for chunk in rendered.chunks:
            if not chunk.get("text"):
                issues.append(
                    ReportIssue(level="error", message="Chunk is empty.", code="chunk_empty")
                )
            if require_content_organization:
                issues.extend(self._validate_organized_chunk(chunk))
            for source_index, source_block_id in enumerate(
                chunk.get("source_block_ids", [])
            ):
                if source_block_id not in block_ids:
                    issues.append(
                        ReportIssue(
                            level="error",
                            message="Chunk source block does not exist.",
                            stage="schema_validation",
                            path=(
                                f"chunks.{chunk.get('chunk_id')}."
                                f"source_block_ids[{source_index}]"
                            ),
                            code="chunk_source_missing",
                        )
                    )

        error_count = sum(1 for issue in issues if issue.level == "error")
        warning_count = sum(1 for issue in issues if issue.level == "warning")
        failure_type_counts: dict[str, int] = {}
        for issue in issues:
            if issue.failure_type:
                failure_type_counts[issue.failure_type] = (
                    failure_type_counts.get(issue.failure_type, 0) + 1
                )
        schema_valid = error_count == 0
        return ValidationReport(
            task_id=task_id,
            schema_id=schema.schema_id,
            passed=schema_valid,
            schema_valid=schema_valid,
            strict_semantic_valid=schema_valid,
            summary={
                "error_count": error_count,
                "warning_count": warning_count,
                "failure_type_counts": failure_type_counts,
            },
            issues=issues,
        )

    def _validate_field(
        self, field: TargetField, value: object, *, path: str
    ) -> list[ReportIssue]:
        issues: list[ReportIssue] = []
        if field.type in {"string", "text", "enum"} and not isinstance(value, str):
            issues.append(self._type_issue(field, "string", path))
        elif field.type == "number" and (
            not isinstance(value, int | float) or isinstance(value, bool)
        ):
            issues.append(self._type_issue(field, "number", path))
        elif field.type == "boolean" and not isinstance(value, bool):
            issues.append(self._type_issue(field, "boolean", path))
        elif field.type == "date" and (
            not isinstance(value, str)
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)
            or not self._valid_date(value)
        ):
            issues.append(
                ReportIssue(
                    level="error",
                    message="Date field must be YYYY-MM-DD.",
                    stage="schema_validation",
                    field_id=field.field_id,
                    path=path,
                    code="date_format_invalid",
                    failure_type="date_format_invalid",
                    source_value=value,
                    suggested_normalized_value=self._suggest_date(value, field),
                )
            )
        elif field.type == "datetime" and (
            not isinstance(value, str)
            or not re.fullmatch(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
                r"(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?",
                value,
            )
            or not self._valid_datetime(value)
        ):
            issues.append(
                ReportIssue(
                    level="error",
                    message="Datetime field must use ISO 8601 date-time format.",
                    stage="schema_validation",
                    field_id=field.field_id,
                    path=path,
                    code="datetime_format_invalid",
                    failure_type="date_format_invalid",
                    source_value=value,
                )
            )
        elif field.type.startswith("array") and not isinstance(value, list):
            issues.append(self._type_issue(field, "array", path))
        elif field.type == "array[string]" and isinstance(value, list):
            invalid_index = next(
                (
                    index
                    for index, item in enumerate(value)
                    if not isinstance(item, str) or not item.strip()
                ),
                None,
            )
            if invalid_index is not None:
                issues.append(
                    ReportIssue(
                        level="error",
                        message="Array field contains an invalid string item.",
                        stage="schema_validation",
                        field_id=field.field_id,
                        path=f"{path}[{invalid_index}]",
                        code="array_item_invalid",
                        failure_type="array_item_invalid",
                        source_value=value,
                    )
                )
        elif field.type == "array[object]" and isinstance(value, list):
            invalid_index = next(
                (index for index, item in enumerate(value) if not isinstance(item, dict)),
                None,
            )
            if invalid_index is not None:
                issues.append(
                    ReportIssue(
                        level="error",
                        message="Array field contains an invalid object item.",
                        stage="schema_validation",
                        field_id=field.field_id,
                        path=f"{path}[{invalid_index}]",
                        code="array_item_invalid",
                        failure_type="array_item_invalid",
                        source_value=value,
                    )
                )
        elif field.type == "object" and not isinstance(value, dict):
            issues.append(self._type_issue(field, "object", path))

        enum_values = field.constraints.get("enum")
        if enum_values and isinstance(value, str) and value not in enum_values:
            issues.append(
                ReportIssue(
                    level="error",
                    message="Enum field has unsupported value.",
                    stage="schema_validation",
                    field_id=field.field_id,
                    path=path,
                    code="enum_value_invalid",
                    failure_type="enum_invalid",
                    source_value=value,
                )
            )
        if isinstance(value, str):
            min_length = field.constraints.get("min_length")
            max_length = field.constraints.get("max_length")
            pattern = field.constraints.get("pattern")
            if isinstance(min_length, int) and len(value) < min_length:
                issues.append(
                    self._constraint_issue(field, path, "min_length_violation")
                )
            if isinstance(max_length, int) and len(value) > max_length:
                issues.append(
                    self._constraint_issue(field, path, "max_length_violation")
                )
            if isinstance(pattern, str) and re.fullmatch(pattern, value) is None:
                issues.append(self._constraint_issue(field, path, "pattern_mismatch"))
        if isinstance(value, int | float) and not isinstance(value, bool):
            minimum = field.constraints.get("minimum")
            maximum = field.constraints.get("maximum")
            if isinstance(minimum, int | float) and value < minimum:
                issues.append(self._constraint_issue(field, path, "minimum_violation"))
            if isinstance(maximum, int | float) and value > maximum:
                issues.append(self._constraint_issue(field, path, "maximum_violation"))
        if field.type == "object" and isinstance(value, dict):
            issues.extend(self._validate_nested_object(field, value, path))
        return issues

    @staticmethod
    def _validate_organized_chunk(chunk: dict) -> list[ReportIssue]:
        issues: list[ReportIssue] = []
        chunk_id = chunk.get("chunk_id")
        if "summary" not in chunk:
            issues.append(
                ReportIssue(
                    level="error",
                    message="Organized chunk is missing summary.",
                    path=chunk_id,
                    code="chunk_summary_missing",
                )
            )
        if not isinstance(chunk.get("keywords"), list):
            issues.append(
                ReportIssue(
                    level="error",
                    message="Organized chunk keywords must be a list.",
                    path=chunk_id,
                    code="chunk_keywords_missing",
                )
            )
        if not isinstance(chunk.get("tags"), dict):
            issues.append(
                ReportIssue(
                    level="error",
                    message="Organized chunk tags must be an object.",
                    path=chunk_id,
                    code="chunk_tags_missing",
                )
            )
        if not chunk.get("source_block_ids") and not chunk.get("source_links"):
            issues.append(
                ReportIssue(
                    level="error",
                    message="Organized chunk must keep source block ids or source links.",
                    path=chunk_id,
                    code="chunk_source_links_missing",
                )
            )
        return issues

    @staticmethod
    def _type_issue(field: TargetField, expected: str, path: str) -> ReportIssue:
        return ReportIssue(
            level="error",
            message=f"Field must be {expected}.",
            stage="schema_validation",
            field_id=field.field_id,
            path=path,
            code="field_type_invalid",
            failure_type="wrong_type",
        )

    @staticmethod
    def _constraint_issue(
        field: TargetField, path: str, code: str
    ) -> ReportIssue:
        return ReportIssue(
            level="error",
            message=f"Field violates {code}.",
            stage="schema_validation",
            field_id=field.field_id,
            path=path,
            code=code,
            failure_type="constraint_violation",
        )

    def _validate_nested_object(
        self, field: TargetField, value: dict, path: str
    ) -> list[ReportIssue]:
        properties = field.constraints.get("properties", {})
        if not isinstance(properties, dict):
            return []
        issues: list[ReportIssue] = []
        for name, rule in properties.items():
            if not isinstance(rule, dict):
                continue
            nested_path = f"{path}.{name}"
            if rule.get("required") and name not in value:
                issues.append(
                    self._constraint_issue(field, nested_path, "nested_required_missing")
                )
            elif name in value:
                expected_type = rule.get("type")
                matches = {
                    "string": isinstance(value[name], str),
                    "number": isinstance(value[name], int | float)
                    and not isinstance(value[name], bool),
                    "object": isinstance(value[name], dict),
                    "array": isinstance(value[name], list),
                    "boolean": isinstance(value[name], bool),
                }.get(expected_type, True)
                if not matches:
                    issues.append(
                        self._constraint_issue(field, nested_path, "nested_type_invalid")
                    )
        if field.constraints.get("additional_properties") is False:
            for name in value.keys() - properties.keys():
                issues.append(
                    self._constraint_issue(
                        field, f"{path}.{name}", "unexpected_field"
                    )
                )
        return issues

    @staticmethod
    def _suggest_date(value: object, field: TargetField) -> object | None:
        normalized, error = TransformService._normalize_date(value, field)
        return normalized if error is None and normalized != value else None

    @staticmethod
    def _valid_date(value: str) -> bool:
        try:
            date.fromisoformat(value)
        except ValueError:
            return False
        return True

    @staticmethod
    def _valid_datetime(value: str) -> bool:
        try:
            normalized = value.removesuffix("Z")
            if value.endswith("Z"):
                normalized += "+00:00"
            datetime.fromisoformat(normalized)
        except ValueError:
            return False
        return True
