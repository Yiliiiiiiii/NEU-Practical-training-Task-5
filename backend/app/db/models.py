from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


class Document(Base):
    __tablename__ = "documents"

    doc_id: Mapped[str] = mapped_column(Text, primary_key=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    uir_version: Mapped[str] = mapped_column(Text)
    source_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_path: Mapped[str] = mapped_column(Text)
    block_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ConversionTask(Base):
    __tablename__ = "conversion_tasks"

    task_id: Mapped[str] = mapped_column(Text, primary_key=True)
    parent_task_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    doc_id: Mapped[str] = mapped_column(Text, ForeignKey("documents.doc_id"))
    schema_id: Mapped[str] = mapped_column(Text, ForeignKey("target_schemas.schema_id"))
    schema_version: Mapped[str] = mapped_column(Text)
    template_id: Mapped[str] = mapped_column(Text, ForeignKey("mapping_templates.template_id"))
    template_version: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    input_hash: Mapped[str] = mapped_column(Text)
    options_json: Mapped[str] = mapped_column(Text, default="{}")
    config_snapshot_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class TargetSchemaRecord(Base):
    __tablename__ = "target_schemas"

    schema_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(Text)
    schema_json: Mapped[str] = mapped_column(Text)
    json_schema: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class MappingTemplateRecord(Base):
    __tablename__ = "mapping_templates"

    template_id: Mapped[str] = mapped_column(Text, primary_key=True)
    schema_id: Mapped[str] = mapped_column(Text, ForeignKey("target_schemas.schema_id"))
    name: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(Text)
    template_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class FieldCandidateRecord(Base):
    __tablename__ = "field_candidates"

    candidate_id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, ForeignKey("conversion_tasks.task_id"))
    doc_id: Mapped[str] = mapped_column(Text, ForeignKey("documents.doc_id"))
    source_path: Mapped[str] = mapped_column(Text)
    source_name: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_sample: Mapped[str | None] = mapped_column(Text, nullable=True)
    inferred_type: Mapped[str] = mapped_column(Text)
    source_blocks_json: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class FieldMappingRecord(Base):
    __tablename__ = "field_mappings"

    mapping_id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, ForeignKey("conversion_tasks.task_id"))
    candidate_id: Mapped[str] = mapped_column(Text, ForeignKey("field_candidates.candidate_id"))
    target_field_id: Mapped[str] = mapped_column(Text)
    method: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(Text)
    need_review: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class TransformTraceRecord(Base):
    __tablename__ = "transform_traces"

    trace_id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, ForeignKey("conversion_tasks.task_id"))
    stage: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    target_field_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    before_json: Mapped[str] = mapped_column(Text, default="{}")
    after_json: Mapped[str] = mapped_column(Text, default="{}")
    rule_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CanonicalModelRecord(Base):
    __tablename__ = "canonical_models"

    task_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("conversion_tasks.task_id"),
        primary_key=True,
    )
    doc_id: Mapped[str] = mapped_column(Text)
    schema_id: Mapped[str] = mapped_column(Text)
    model_json: Mapped[str] = mapped_column(Text)
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ValidationReportRecord(Base):
    __tablename__ = "validation_reports"

    report_id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, ForeignKey("conversion_tasks.task_id"))
    passed: Mapped[bool] = mapped_column(Boolean)
    error_count: Mapped[int] = mapped_column(Integer)
    warning_count: Mapped[int] = mapped_column(Integer)
    report_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ConsistencyReportRecord(Base):
    __tablename__ = "consistency_reports"

    report_id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, ForeignKey("conversion_tasks.task_id"))
    passed: Mapped[bool] = mapped_column(Boolean)
    error_count: Mapped[int] = mapped_column(Integer)
    warning_count: Mapped[int] = mapped_column(Integer)
    report_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class OutputPackageRecord(Base):
    __tablename__ = "output_packages"

    package_id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, ForeignKey("conversion_tasks.task_id"))
    doc_id: Mapped[str] = mapped_column(Text)
    zip_path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PackageFileRecord(Base):
    __tablename__ = "package_files"

    file_id: Mapped[str] = mapped_column(Text, primary_key=True)
    package_id: Mapped[str] = mapped_column(Text, ForeignKey("output_packages.package_id"))
    relative_path: Mapped[str] = mapped_column(Text)
    media_type: Mapped[str] = mapped_column(Text)
    bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(Text)


class ReviewRecord(Base):
    __tablename__ = "review_records"

    review_id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, ForeignKey("conversion_tasks.task_id"))
    mapping_id: Mapped[str] = mapped_column(Text, ForeignKey("field_mappings.mapping_id"))
    old_target_field_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_target_field_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision: Mapped[str] = mapped_column(Text)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RealRunRecord(Base):
    __tablename__ = "real_runs"

    real_run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, ForeignKey("conversion_tasks.task_id"))
    doc_id: Mapped[str] = mapped_column(Text)
    schema_id: Mapped[str] = mapped_column(Text)
    template_id: Mapped[str] = mapped_column(Text)
    input_hash: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    summary_json: Mapped[str] = mapped_column(Text, default="{}")
    report_paths_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LearningCandidateRecord(Base):
    __tablename__ = "learning_candidates"

    candidate_id: Mapped[str] = mapped_column(Text, primary_key=True)
    real_run_id: Mapped[str] = mapped_column(Text, ForeignKey("real_runs.real_run_id"))
    task_id: Mapped[str] = mapped_column(Text, ForeignKey("conversion_tasks.task_id"))
    candidate_type: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="pending")
    risk_level: Mapped[str] = mapped_column(Text)
    target_field_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_payload_json: Mapped[str] = mapped_column(Text, default="{}")
    final_payload_json: Mapped[str] = mapped_column(Text, default="{}")
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    generator: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class KnowledgePackRecord(Base):
    __tablename__ = "knowledge_packs"

    pack_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    scope_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(Text, default="draft")
    version: Mapped[str] = mapped_column(Text)
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    regression_report_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class KnowledgePackItemRecord(Base):
    __tablename__ = "knowledge_pack_items"

    item_id: Mapped[str] = mapped_column(Text, primary_key=True)
    pack_id: Mapped[str] = mapped_column(Text, ForeignKey("knowledge_packs.pack_id"))
    item_type: Mapped[str] = mapped_column(Text)
    target_field_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    source_candidate_id: Mapped[str | None] = mapped_column(
        Text,
        ForeignKey("learning_candidates.candidate_id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
