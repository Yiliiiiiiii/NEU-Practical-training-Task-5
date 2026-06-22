from app.schemas.target_schema import TargetSchema


class SchemaValidationError(ValueError):
    pass


def validate_target_schema(schema: TargetSchema) -> None:
    seen: set[str] = set()
    for field in schema.fields:
        if field.field_id in seen:
            raise SchemaValidationError(f"duplicate field_id: {field.field_id}")
        seen.add(field.field_id)

    if schema.json_schema.get("type") != "object":
        raise SchemaValidationError("json_schema.type must be object")
