import re

from app.schemas.reports import ReportIssue, ValidationReport
from app.schemas.target_schema import TargetField, TargetSchema
from app.services.render_service import RenderedArtifacts


class ValidationService:
    def validate(
        self,
        task_id: str,
        schema: TargetSchema,
        rendered: RenderedArtifacts,
        require_content_organization: bool = False,
    ) -> ValidationReport:
        issues: list[ReportIssue] = []
        data = rendered.structured_json.get("data", {})

        for field in schema.fields:
            if field.required and field.field_id not in data:
                issues.append(
                    ReportIssue(
                        level="error",
                        message="Required field is missing.",
                        field_id=field.field_id,
                        code="required_field_missing",
                    )
                )
                continue
            if field.field_id in data:
                issues.extend(self._validate_field(field, data[field.field_id]))

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
            for source_block_id in chunk.get("source_block_ids", []):
                if source_block_id not in block_ids:
                    issues.append(
                        ReportIssue(
                            level="error",
                            message="Chunk source block does not exist.",
                            path=chunk.get("chunk_id"),
                            code="chunk_source_missing",
                        )
                    )

        error_count = sum(1 for issue in issues if issue.level == "error")
        warning_count = sum(1 for issue in issues if issue.level == "warning")
        return ValidationReport(
            task_id=task_id,
            schema_id=schema.schema_id,
            passed=error_count == 0,
            summary={"error_count": error_count, "warning_count": warning_count},
            issues=issues,
        )

    def _validate_field(self, field: TargetField, value: object) -> list[ReportIssue]:
        issues: list[ReportIssue] = []
        if field.type in {"string", "text", "enum"} and not isinstance(value, str):
            issues.append(self._type_issue(field, "string"))
        elif field.type == "number" and not isinstance(value, int | float):
            issues.append(self._type_issue(field, "number"))
        elif field.type == "date" and (
            not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)
        ):
            issues.append(
                ReportIssue(
                    level="error",
                    message="Date field must be YYYY-MM-DD.",
                    field_id=field.field_id,
                    code="date_format_invalid",
                )
            )
        elif field.type.startswith("array") and not isinstance(value, list):
            issues.append(self._type_issue(field, "array"))
        elif field.type == "object" and not isinstance(value, dict):
            issues.append(self._type_issue(field, "object"))

        enum_values = field.constraints.get("enum")
        if enum_values and isinstance(value, str) and value not in enum_values:
            issues.append(
                ReportIssue(
                    level="error",
                    message="Enum field has unsupported value.",
                    field_id=field.field_id,
                    code="enum_value_invalid",
                )
            )
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
    def _type_issue(field: TargetField, expected: str) -> ReportIssue:
        return ReportIssue(
            level="error",
            message=f"Field must be {expected}.",
            field_id=field.field_id,
            code="field_type_invalid",
        )
