from datetime import date
from typing import Any

from app.schemas.reports import ReportIssue, ValidationReport
from app.schemas.target_schema import TargetSchema


def validate_content_data(
    task_id: str,
    schema_id: str,
    data: dict,
    target_schema: TargetSchema,
) -> ValidationReport:
    issues: list[ReportIssue] = []
    schema_props = target_schema.json_schema.get("properties", {})
    schema_required = set(target_schema.json_schema.get("required", []))
    field_required = {field.field_id for field in target_schema.fields if field.required}
    required_fields = schema_required | field_required

    for field in target_schema.fields:
        fid = field.field_id
        value = data.get(fid)
        prop = schema_props.get(fid, {})

        if fid in required_fields and (value is None or value == ""):
            issues.append(ReportIssue(
                level="error",
                code="required_missing",
                message=f"required field '{fid}' is missing or empty",
                field_id=fid,
                path=f"data.{fid}",
            ))
            continue

        if value is None:
            continue

        expected_type = _expected_type(prop, field.type)
        type_ok = _check_type(value, expected_type)
        if not type_ok:
            code = "date_format_mismatch" if expected_type == "date" else "type_mismatch"
            issues.append(ReportIssue(
                level="warning",
                code=code,
                message=(
                    f"field '{fid}' expected type '{expected_type}', "
                    f"got '{type(value).__name__}'"
                ),
                field_id=fid,
                path=f"data.{fid}",
            ))

        min_value = _first_present(prop, field.constraints, "minimum", "min")
        if min_value is not None and _is_json_number(value) and value < min_value:
            issues.append(ReportIssue(
                level="warning",
                code="minimum_violation",
                message=f"field '{fid}' value {value} < minimum {min_value}",
                field_id=fid,
                path=f"data.{fid}",
            ))

        max_value = _first_present(prop, field.constraints, "maximum", "max")
        if max_value is not None and _is_json_number(value) and value > max_value:
            issues.append(ReportIssue(
                level="warning",
                code="maximum_violation",
                message=f"field '{fid}' value {value} > maximum {max_value}",
                field_id=fid,
                path=f"data.{fid}",
            ))

        exclusive_min = _first_present(prop, field.constraints, "exclusiveMinimum")
        if exclusive_min is not None and _is_json_number(value) and value <= exclusive_min:
            issues.append(ReportIssue(
                level="warning",
                code="exclusive_minimum_violation",
                message=f"field '{fid}' value {value} <= exclusive minimum {exclusive_min}",
                field_id=fid,
                path=f"data.{fid}",
            ))

        exclusive_max = _first_present(prop, field.constraints, "exclusiveMaximum")
        if exclusive_max is not None and _is_json_number(value) and value >= exclusive_max:
            issues.append(ReportIssue(
                level="warning",
                code="exclusive_maximum_violation",
                message=f"field '{fid}' value {value} >= exclusive maximum {exclusive_max}",
                field_id=fid,
                path=f"data.{fid}",
            ))

        enum_vals = prop.get("enum") or field.constraints.get("enum")
        if enum_vals and value not in enum_vals:
            issues.append(ReportIssue(
                level="error",
                code="enum_violation",
                message=f"field '{fid}' value '{value}' not in allowed values {enum_vals}",
                field_id=fid,
                path=f"data.{fid}",
            ))

        pattern = prop.get("pattern") or field.constraints.get("pattern")
        if pattern and isinstance(value, str):
            import re
            if not re.search(pattern, value):
                issues.append(ReportIssue(
                    level="warning",
                    code="pattern_mismatch",
                    message=f"field '{fid}' value does not match pattern '{pattern}'",
                    field_id=fid,
                    path=f"data.{fid}",
                ))

        min_len = prop.get("minLength") or field.constraints.get("min_length")
        if min_len is not None and isinstance(value, str) and len(value) < min_len:
            issues.append(ReportIssue(
                level="warning",
                code="min_length_violation",
                message=f"field '{fid}' length {len(value)} < minimum {min_len}",
                field_id=fid,
                path=f"data.{fid}",
            ))

        max_len = prop.get("maxLength") or field.constraints.get("max_length")
        if max_len is not None and isinstance(value, str) and len(value) > max_len:
            issues.append(ReportIssue(
                level="warning",
                code="max_length_violation",
                message=f"field '{fid}' length {len(value)} > maximum {max_len}",
                field_id=fid,
                path=f"data.{fid}",
            ))

    error_count = sum(1 for i in issues if i.level == "error")
    warning_count = sum(1 for i in issues if i.level == "warning")
    passed = error_count == 0

    return ValidationReport(
        task_id=task_id,
        schema_id=schema_id,
        passed=passed,
        summary={
            "error_count": error_count,
            "warning_count": warning_count,
            "check_count": len(issues),
        },
        issues=issues,
    )


def _expected_type(prop: dict[str, Any], field_type: str) -> str:
    if prop.get("format") == "date" or field_type == "date":
        return "date"
    return prop.get("type") or field_type


def _first_present(primary: dict[str, Any], secondary: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in primary:
            return primary[key]
        if key in secondary:
            return secondary[key]
    return None


def _is_json_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _check_type(value, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type in {"integer", "int"}:
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type in {"number", "float"}:
        return _is_json_number(value)
    if expected_type in {"boolean", "bool"}:
        return isinstance(value, bool)
    if expected_type == "date":
        if not isinstance(value, str):
            return False
        try:
            date.fromisoformat(value)
        except ValueError:
            return False
        return True
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "object":
        return isinstance(value, dict)
    return True
