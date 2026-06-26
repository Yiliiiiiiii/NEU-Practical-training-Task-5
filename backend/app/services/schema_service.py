import json
from pathlib import Path

from app.schemas.target_schema import TargetField, TargetSchema

DEFAULT_SCHEMA_DIR = (
    Path(__file__).resolve().parents[3] / "examples" / "production_like" / "schemas"
)


class SchemaService:
    VALID_FIELD_TYPES = {
        "array",
        "array[object]",
        "array[string]",
        "boolean",
        "date",
        "enum",
        "number",
        "object",
        "string",
        "text",
    }

    def __init__(self, schemas_dir: str | Path = DEFAULT_SCHEMA_DIR) -> None:
        self.schemas_dir = Path(schemas_dir)

    def list_schemas(self) -> list[TargetSchema]:
        schemas = [self._load_schema_file(path) for path in self._schema_paths()]
        return sorted(schemas, key=lambda schema: (schema.schema_id, schema.version))

    def load_schema(self, schema_id: str, version: str | None = None) -> TargetSchema:
        for path in self._schema_paths():
            schema = self._load_schema_file(path)
            if schema.schema_id == schema_id and (version is None or schema.version == version):
                return schema
        version_text = f" version {version}" if version is not None else ""
        raise LookupError(f"schema {schema_id}{version_text} not found")

    def validate_schema(self, schema: TargetSchema) -> TargetSchema:
        if not schema.schema_id:
            raise ValueError("schema_id is required")
        if not schema.version:
            raise ValueError("schema version is required")

        field_ids: set[str] = set()
        field_names: set[str] = set()
        for field in schema.fields:
            if field.field_id in field_ids:
                raise ValueError(f"duplicate field id: {field.field_id}")
            field_ids.add(field.field_id)

            if field.name in field_names:
                raise ValueError(f"duplicate field name: {field.name}")
            field_names.add(field.name)

            if field.type not in self.VALID_FIELD_TYPES:
                raise ValueError(f"unsupported field type: {field.type}")
            if not isinstance(field.required, bool):
                raise ValueError(f"field required must be boolean: {field.field_id}")
            if field.type == "enum":
                enum_values = field.constraints.get("enum")
                if not isinstance(enum_values, list) or not enum_values:
                    raise ValueError(f"enum field must define constraints.enum: {field.field_id}")
                if not all(isinstance(value, str) for value in enum_values):
                    raise ValueError(f"enum values must be strings: {field.field_id}")

        return schema

    @staticmethod
    def get_required_fields(schema: TargetSchema) -> list[TargetField]:
        return [field for field in schema.fields if field.required]

    @staticmethod
    def get_field(schema: TargetSchema, field_name: str) -> TargetField:
        for field in schema.fields:
            if field_name in {
                field.field_id,
                field.name,
                field.display_name,
                *field.aliases,
            }:
                return field
        raise LookupError(f"field {field_name} not found in schema {schema.schema_id}")

    def _schema_paths(self) -> list[Path]:
        return sorted(self.schemas_dir.glob("*.json"))

    def _load_schema_file(self, path: Path) -> TargetSchema:
        schema = TargetSchema.model_validate(json.loads(path.read_text(encoding="utf-8")))
        return self.validate_schema(schema)
