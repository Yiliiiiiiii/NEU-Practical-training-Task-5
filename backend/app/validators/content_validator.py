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

    for field in target_schema.fields:
        fid = field.field_id
        value = data.get(fid)
        prop = schema_props.get(fid, {})

        if fid in schema_required and (value is None or value == ""):
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

        expected_type = prop.get("type") or field.type
        type_ok = _check_type(value, expected_type)
        if not type_ok:
            issues.append(ReportIssue(
                level="warning",
                code="type_mismatch",
                message=(
                    f"field '{fid}' expected type '{expected_type}', "
                    f"got '{type(value).__name__}'"
                ),
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


def _check_type(value, expected_type: str) -> bool:
    type_map = {
        "string": str,
        "integer": int,
        "int": int,
        "number": (int, float),
        "float": (int, float),
        "boolean": bool,
        "bool": bool,
        "array": list,
        "object": dict,
    }
    expected = type_map.get(expected_type)
    if expected is None:
        return True
    return isinstance(value, expected)
