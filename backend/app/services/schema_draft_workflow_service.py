from datetime import UTC, datetime

from app.schemas.schema_draft import (
    DraftRiskReport,
    FieldDiscoveryResult,
    SchemaDraftExportResponse,
    SchemaDraftPackage,
    SchemaDraftReport,
)
from app.schemas.uir import UIRDocument
from app.services.draft_risk_service import DraftRiskService
from app.services.field_discovery_service import FieldDiscoveryService
from app.services.schema_draft_service import SchemaDraftService
from app.services.storage_service import StorageService
from app.services.template_draft_service import TemplateDraftService
from app.utils.ids import new_id


class SchemaDraftWorkflowService:
    def __init__(
        self,
        storage: StorageService,
        *,
        discovery_service: FieldDiscoveryService | None = None,
        schema_service: SchemaDraftService | None = None,
        template_service: TemplateDraftService | None = None,
        risk_service: DraftRiskService | None = None,
    ) -> None:
        self.storage = storage
        self.discovery_service = discovery_service or FieldDiscoveryService()
        self.schema_service = schema_service or SchemaDraftService()
        self.template_service = template_service or TemplateDraftService()
        self.risk_service = risk_service or DraftRiskService()

    def discover(self, documents: list[UIRDocument]) -> FieldDiscoveryResult:
        return self.discovery_service.discover(documents)

    def generate(
        self,
        documents: list[UIRDocument],
        *,
        schema_id: str,
        schema_name: str,
        template_id: str,
    ) -> SchemaDraftPackage:
        discovery = self.discover(documents)
        draft_schema = self.schema_service.generate(
            discovery,
            schema_id=schema_id,
            name=schema_name,
        )
        draft_template = self.template_service.generate(
            discovery,
            schema_id=schema_id,
            template_id=template_id,
        )
        risk_report = self.risk_service.scan(draft_schema, draft_template)
        draft_id = new_id("draft")
        package = SchemaDraftPackage(
            draft_id=draft_id,
            created_at=datetime.now(UTC).isoformat(),
            discovery=discovery,
            draft_schema=draft_schema,
            draft_template=draft_template,
            risk_report=risk_report,
            draft_report=self._draft_report(
                documents=documents,
                discovery=discovery,
                risk_report=risk_report,
            ),
            must_not_auto_activate=True,
        )
        self._save(package)
        return package

    def get(self, draft_id: str) -> SchemaDraftPackage:
        try:
            payload = self.storage.read_json(self._package_path(draft_id))
        except FileNotFoundError as exc:
            raise LookupError("schema draft not found") from exc
        return SchemaDraftPackage.model_validate(payload)

    def validate(self, draft_id: str) -> DraftRiskReport:
        package = self.get(draft_id)
        risk_report = self.risk_service.scan(
            package.draft_schema,
            package.draft_template,
        )
        package.risk_report = risk_report
        package.draft_report.risk_count = risk_report.risk_count
        package.draft_report.badcase_violations = risk_report.badcase_violations
        package.draft_report.llm_auto_accepted_count = (
            risk_report.llm_auto_accepted_count
        )
        self._save(package)
        return risk_report

    def export(self, draft_id: str) -> SchemaDraftExportResponse:
        package = self.get(draft_id)
        base = f"schema_drafts/{draft_id}/export"
        files = {
            "draft_schema": f"{base}/draft_schema.json",
            "draft_template": f"{base}/draft_template.json",
            "draft_report": f"{base}/draft_report.json",
            "risk_report": f"{base}/risk_report.json",
        }
        payloads = {
            "draft_schema": package.draft_schema,
            "draft_template": package.draft_template,
            "draft_report": package.draft_report,
            "risk_report": package.risk_report,
        }
        for key, relative_path in files.items():
            self.storage.save_json(
                relative_path,
                payloads[key].model_dump(mode="json"),
            )
        return SchemaDraftExportResponse(
            draft_id=draft_id,
            files=files,
            sha256={
                key: self.storage.sha256(relative_path)
                for key, relative_path in files.items()
            },
            must_not_auto_activate=True,
        )

    def _save(self, package: SchemaDraftPackage) -> None:
        self.storage.save_json(
            self._package_path(package.draft_id),
            package.model_dump(mode="json"),
        )

    @staticmethod
    def _package_path(draft_id: str) -> str:
        return f"schema_drafts/{draft_id}/draft_package.json"

    @staticmethod
    def _draft_report(
        *,
        documents: list[UIRDocument],
        discovery: FieldDiscoveryResult,
        risk_report: DraftRiskReport,
    ) -> SchemaDraftReport:
        return SchemaDraftReport(
            sample_count=len(documents),
            candidate_count=len(discovery.field_candidates),
            source_doc_ids=[document.doc_id for document in documents],
            deterministic=True,
            must_not_auto_activate=True,
            risk_count=risk_report.risk_count,
            badcase_violations=risk_report.badcase_violations,
            llm_auto_accepted_count=risk_report.llm_auto_accepted_count,
            secret_leak_count=0,
        )
