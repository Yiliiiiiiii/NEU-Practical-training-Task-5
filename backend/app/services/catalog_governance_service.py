import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ConversionTask,
    MappingTemplateRecord,
    TargetSchemaRecord,
)
from app.schemas.mapping_template import MappingTemplate
from app.schemas.target_schema import TargetSchema
from app.services.schema_service import SchemaService
from app.services.template_service import TemplateService


class CatalogGovernanceService:
    VALID_STATUSES = {"draft", "active", "archived"}

    def __init__(
        self,
        db: Session,
        schema_service: SchemaService | None = None,
        template_service: TemplateService | None = None,
    ) -> None:
        self.db = db
        self.schema_service = schema_service or SchemaService()
        self.template_service = template_service or TemplateService()

    def seed_from_files(self) -> None:
        for schema in self.schema_service.list_schemas():
            if self._get_schema_record(schema.schema_id, schema.version) is None:
                self.create_schema(schema, status="active")
        for template in self.template_service.list_templates():
            if self._get_template_record(template.template_id, template.version) is None:
                self.create_template(template, status="active", seed_catalog=False)

    def list_schema_records(self) -> list[TargetSchemaRecord]:
        self.seed_from_files()
        return self._schema_records()

    def _schema_records(self) -> list[TargetSchemaRecord]:
        return list(
            self.db.scalars(
                select(TargetSchemaRecord).order_by(
                    TargetSchemaRecord.schema_id,
                    TargetSchemaRecord.version,
                )
            )
        )

    def load_schema(self, schema_id: str, version: str | None = None) -> TargetSchema:
        self.seed_from_files()
        record = self._select_schema_record(schema_id, version)
        if record is None or record.status == "archived":
            version_text = f" version {version}" if version is not None else ""
            raise LookupError(f"schema {schema_id}{version_text} not found")
        return TargetSchema.model_validate(json.loads(record.schema_json))

    def create_schema(self, schema: TargetSchema, status: str = "draft") -> TargetSchemaRecord:
        self._validate_status(status)
        self.schema_service.validate_schema(schema)
        if self._get_schema_record(schema.schema_id, schema.version) is not None:
            raise ValueError("schema version already exists")
        payload = schema.model_dump(mode="json")
        record = TargetSchemaRecord(
            record_id=f"{schema.schema_id}:{schema.version}",
            schema_id=schema.schema_id,
            name=schema.name,
            version=schema.version,
            status=status,
            schema_json=json.dumps(payload, ensure_ascii=False, sort_keys=True),
            json_schema=json.dumps(schema.json_schema, ensure_ascii=False, sort_keys=True),
            content_hash=self._hash(payload),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def activate_schema(self, schema_id: str, version: str) -> TargetSchemaRecord:
        record = self._require_schema_record(schema_id, version)
        record.status = "active"
        record.updated_at = self._now()
        self.db.commit()
        self.db.refresh(record)
        return record

    def archive_schema(self, schema_id: str, version: str) -> TargetSchemaRecord:
        record = self._require_schema_record(schema_id, version)
        if self._schema_is_referenced(schema_id, version):
            raise ValueError("referenced schema version cannot be archived")
        record.status = "archived"
        record.archived_at = self._now()
        record.updated_at = self._now()
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_template_records(self) -> list[MappingTemplateRecord]:
        self.seed_from_files()
        return self._template_records()

    def _template_records(self) -> list[MappingTemplateRecord]:
        return list(
            self.db.scalars(
                select(MappingTemplateRecord).order_by(
                    MappingTemplateRecord.template_id,
                    MappingTemplateRecord.version,
                )
            )
        )

    def load_template(self, template_id: str, version: str | None = None) -> MappingTemplate:
        self.seed_from_files()
        record = self._select_template_record(template_id, version)
        if record is None or record.status == "archived":
            version_text = f" version {version}" if version is not None else ""
            raise LookupError(f"template {template_id}{version_text} not found")
        return MappingTemplate.model_validate(json.loads(record.template_json))

    def create_template(
        self,
        template: MappingTemplate,
        status: str = "draft",
        seed_catalog: bool = True,
    ) -> MappingTemplateRecord:
        self._validate_status(status)
        if seed_catalog:
            self.seed_from_files()
        schema_record = self._select_schema_record(template.schema_id, version=None)
        if schema_record is None or schema_record.status == "archived":
            raise LookupError(f"schema {template.schema_id} not found")
        schema = TargetSchema.model_validate(json.loads(schema_record.schema_json))
        self.template_service.validate_template(template, schema)
        if self._get_template_record(template.template_id, template.version) is not None:
            raise ValueError("template version already exists")
        payload = template.model_dump(mode="json")
        record = MappingTemplateRecord(
            record_id=f"{template.template_id}:{template.version}",
            template_id=template.template_id,
            schema_id=template.schema_id,
            name=template.name,
            version=template.version,
            status=status,
            template_json=json.dumps(payload, ensure_ascii=False, sort_keys=True),
            content_hash=self._hash(payload),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def activate_template(self, template_id: str, version: str) -> MappingTemplateRecord:
        record = self._require_template_record(template_id, version)
        record.status = "active"
        record.updated_at = self._now()
        self.db.commit()
        self.db.refresh(record)
        return record

    def archive_template(self, template_id: str, version: str) -> MappingTemplateRecord:
        record = self._require_template_record(template_id, version)
        if self._template_is_referenced(template_id, version):
            raise ValueError("referenced template version cannot be archived")
        record.status = "archived"
        record.archived_at = self._now()
        record.updated_at = self._now()
        self.db.commit()
        self.db.refresh(record)
        return record

    def _select_schema_record(
        self,
        schema_id: str,
        version: str | None,
    ) -> TargetSchemaRecord | None:
        records = [
            record
            for record in self._schema_records()
            if record.schema_id == schema_id and (version is None or record.version == version)
        ]
        if not records:
            return None
        active = [record for record in records if record.status == "active"]
        return sorted(active or records, key=lambda item: item.version)[-1]

    def _select_template_record(
        self,
        template_id: str,
        version: str | None,
    ) -> MappingTemplateRecord | None:
        records = [
            record
            for record in self._template_records()
            if record.template_id == template_id
            and (version is None or record.version == version)
        ]
        if not records:
            return None
        active = [record for record in records if record.status == "active"]
        return sorted(active or records, key=lambda item: item.version)[-1]

    def _get_schema_record(
        self,
        schema_id: str,
        version: str,
    ) -> TargetSchemaRecord | None:
        return self.db.get(TargetSchemaRecord, f"{schema_id}:{version}")

    def _require_schema_record(self, schema_id: str, version: str) -> TargetSchemaRecord:
        record = self._get_schema_record(schema_id, version)
        if record is None:
            raise LookupError("schema version not found")
        return record

    def _get_template_record(
        self,
        template_id: str,
        version: str,
    ) -> MappingTemplateRecord | None:
        return self.db.get(MappingTemplateRecord, f"{template_id}:{version}")

    def _require_template_record(self, template_id: str, version: str) -> MappingTemplateRecord:
        record = self._get_template_record(template_id, version)
        if record is None:
            raise LookupError("template version not found")
        return record

    def _schema_is_referenced(self, schema_id: str, version: str) -> bool:
        return (
            self.db.scalars(
                select(ConversionTask).where(
                    ConversionTask.schema_id == schema_id,
                    ConversionTask.schema_version == version,
                )
            ).first()
            is not None
        )

    def _template_is_referenced(self, template_id: str, version: str) -> bool:
        return (
            self.db.scalars(
                select(ConversionTask).where(
                    ConversionTask.template_id == template_id,
                    ConversionTask.template_version == version,
                )
            ).first()
            is not None
        )

    def _validate_status(self, status: str) -> None:
        if status not in self.VALID_STATUSES:
            raise ValueError("invalid catalog status")

    @staticmethod
    def _hash(payload: dict[str, Any]) -> str:
        data = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return "sha256:" + hashlib.sha256(data).hexdigest()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)
