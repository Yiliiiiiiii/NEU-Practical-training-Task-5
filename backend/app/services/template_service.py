from sqlalchemy.orm import Session

from app.db.models import MappingTemplateRecord, TargetSchemaRecord
from app.schemas.mapping_template import MappingTemplate
from app.schemas.target_schema import TargetSchema
from app.services.storage_service import StorageService


class TemplateValidationError(ValueError):
    pass


class TemplateService:
    def __init__(self, db: Session, storage: StorageService) -> None:
        self.db = db
        self.storage = storage

    def save_template(self, template: MappingTemplate) -> MappingTemplateRecord:
        schema_record = self.db.get(TargetSchemaRecord, template.schema_id)
        if schema_record is None:
            raise LookupError("schema not found")

        schema = TargetSchema.model_validate_json(schema_record.schema_json)
        self._validate_binding(template, schema)

        relative_path = f"templates/{template.template_id}/template.json"
        self.storage.save_json(relative_path, template.model_dump(mode="json"))

        record = self.db.get(MappingTemplateRecord, template.template_id)
        template_json = template.model_dump_json()
        if record is None:
            record = MappingTemplateRecord(
                template_id=template.template_id,
                schema_id=template.schema_id,
                name=template.name,
                version=template.version,
                template_json=template_json,
            )
            self.db.add(record)
        else:
            record.schema_id = template.schema_id
            record.name = template.name
            record.version = template.version
            record.template_json = template_json

        self.db.commit()
        self.db.refresh(record)
        return record

    def list_templates(self) -> list[MappingTemplateRecord]:
        return (
            self.db.query(MappingTemplateRecord)
            .order_by(MappingTemplateRecord.created_at.desc())
            .all()
        )

    def get_template(self, template_id: str) -> MappingTemplateRecord | None:
        return self.db.get(MappingTemplateRecord, template_id)

    @staticmethod
    def parse_template(record: MappingTemplateRecord) -> MappingTemplate:
        return MappingTemplate.model_validate_json(record.template_json)

    @staticmethod
    def _validate_binding(template: MappingTemplate, schema: TargetSchema) -> None:
        target_fields = {field.field_id for field in schema.fields}
        references: list[str] = []

        references.extend(template.aliases.keys())
        references.extend(rule.target_field_id for rule in template.regex_rules)
        references.extend(template.enum_maps.keys())
        for rule in template.transform_rules:
            if rule.target_field_id is not None:
                references.append(rule.target_field_id)
            references.extend(rule.target_fields)

        for field_id in references:
            if field_id not in target_fields:
                raise TemplateValidationError(
                    f"template references unknown target field: {field_id}"
                )
