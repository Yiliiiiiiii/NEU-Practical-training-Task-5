from sqlalchemy.orm import Session

from app.db.models import TargetSchemaRecord
from app.schemas.target_schema import TargetSchema
from app.services.storage_service import StorageService
from app.validators.schema_validator import validate_target_schema


class SchemaService:
    def __init__(self, db: Session, storage: StorageService) -> None:
        self.db = db
        self.storage = storage

    def create_schema(self, schema: TargetSchema) -> TargetSchemaRecord:
        validate_target_schema(schema)
        relative_path = f"schemas/{schema.schema_id}/schema.json"
        self.storage.save_json(relative_path, schema.model_dump(mode="json"))

        record = self.db.get(TargetSchemaRecord, schema.schema_id)
        schema_json = schema.model_dump_json()
        json_schema = schema.model_dump_json(include={"json_schema"})
        if record is None:
            record = TargetSchemaRecord(
                schema_id=schema.schema_id,
                name=schema.name,
                version=schema.version,
                schema_json=schema_json,
                json_schema=json_schema,
            )
            self.db.add(record)
        else:
            record.name = schema.name
            record.version = schema.version
            record.schema_json = schema_json
            record.json_schema = json_schema

        self.db.commit()
        self.db.refresh(record)
        return record

    def list_schemas(self) -> list[TargetSchemaRecord]:
        return (
            self.db.query(TargetSchemaRecord)
            .order_by(TargetSchemaRecord.created_at.desc())
            .all()
        )

    def get_schema(self, schema_id: str) -> TargetSchemaRecord | None:
        return self.db.get(TargetSchemaRecord, schema_id)

    @staticmethod
    def parse_schema(record: TargetSchemaRecord) -> TargetSchema:
        return TargetSchema.model_validate_json(record.schema_json)
