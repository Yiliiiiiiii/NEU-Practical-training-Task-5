import hashlib
import json
from datetime import datetime
from typing import Any

from sqlalchemy import Engine, inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.sql.schema import Table

from app.db.models import (
    Base,
    MappingTemplateRecord,
    TargetSchemaRecord,
)
from app.db.session import engine


def init_db(*, bind: Engine = engine) -> None:
    if bind.dialect.name != "sqlite":
        Base.metadata.create_all(bind=bind)
        return

    with bind.begin() as connection:
        _rebuild_legacy_catalogs(connection)
        Base.metadata.create_all(bind=connection)
        _add_missing_columns(connection)
        _backfill_legacy_rows(connection)


def _rebuild_legacy_catalogs(connection: Connection) -> None:
    _rebuild_legacy_catalog(
        connection,
        table_name="target_schemas",
        table=TargetSchemaRecord.__table__,
        source_id="schema_id",
        payload_field="schema_json",
    )
    _rebuild_legacy_catalog(
        connection,
        table_name="mapping_templates",
        table=MappingTemplateRecord.__table__,
        source_id="template_id",
        payload_field="template_json",
    )


def _rebuild_legacy_catalog(
    connection: Connection,
    *,
    table_name: str,
    table: Table,
    source_id: str,
    payload_field: str,
) -> None:
    inspector = inspect(connection)
    if not inspector.has_table(table_name):
        return
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    if "record_id" in columns:
        return

    rows = connection.execute(text(f'SELECT * FROM "{table_name}"')).mappings().all()
    legacy_name = f"{table_name}_legacy"
    connection.exec_driver_sql(
        f'ALTER TABLE "{table_name}" RENAME TO "{legacy_name}"'
    )
    table.create(bind=connection)
    for row in rows:
        created_at = _as_datetime(row.get("created_at"))
        payload = str(row[payload_field])
        values: dict[str, Any] = {
            "record_id": f"{row[source_id]}:{row['version']}",
            source_id: row[source_id],
            "schema_id": row.get("schema_id", row[source_id]),
            "name": row["name"],
            "version": row["version"],
            "status": "active",
            payload_field: payload,
            "content_hash": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
            "created_at": created_at,
            "updated_at": created_at,
            "archived_at": None,
        }
        if table_name == "target_schemas":
            values["json_schema"] = row["json_schema"]
        connection.execute(table.insert().values(**values))
    connection.exec_driver_sql(f'DROP TABLE "{legacy_name}"')


def _add_missing_columns(connection: Connection) -> None:
    inspector = inspect(connection)
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue
        existing = {
            column["name"] for column in inspect(connection).get_columns(table.name)
        }
        for column in table.columns:
            if column.name in existing:
                continue
            type_sql = column.type.compile(dialect=connection.dialect)
            connection.exec_driver_sql(
                f'ALTER TABLE "{table.name}" '
                f'ADD COLUMN "{column.name}" {type_sql}'
            )


def _backfill_legacy_rows(connection: Connection) -> None:
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())
    if "review_records" in tables:
        connection.exec_driver_sql(
            """
            UPDATE review_records
            SET status = CASE
                    WHEN decision IN ('confirmed', 'approved') THEN 'approved'
                    WHEN decision = 'rejected' THEN 'rejected'
                    ELSE 'pending'
                END,
                updated_at = COALESCE(updated_at, created_at)
            WHERE status IS NULL OR updated_at IS NULL
            """
        )
    if "knowledge_pack_items" in tables:
        columns = {
            column["name"]
            for column in inspector.get_columns("knowledge_pack_items")
        }
        if "payload_json" in columns:
            connection.exec_driver_sql(
                """
                UPDATE knowledge_pack_items
                SET value_json = COALESCE(value_json, payload_json, '{}'),
                    candidate_id = COALESCE(candidate_id, source_candidate_id)
                WHERE value_json IS NULL OR candidate_id IS NULL
                """
            )
    if "knowledge_packs" in tables:
        columns = {
            column["name"] for column in inspector.get_columns("knowledge_packs")
        }
        if "scope_json" not in columns:
            return
        rows = connection.execute(
            text(
                "SELECT pack_id, scope_json, reviewer, created_at "
                "FROM knowledge_packs "
                "WHERE schema_id IS NULL OR template_id IS NULL"
            )
        ).mappings()
        for row in rows:
            scope = _json_object(row.get("scope_json"))
            connection.execute(
                text(
                    """
                    UPDATE knowledge_packs
                    SET schema_id = :schema_id,
                        template_id = :template_id,
                        created_by = COALESCE(created_by, :created_by),
                        metadata_json = COALESCE(metadata_json, :metadata_json),
                        updated_at = COALESCE(updated_at, created_at)
                    WHERE pack_id = :pack_id
                    """
                ),
                {
                    "pack_id": row["pack_id"],
                    "schema_id": str(scope.get("schema_id", "")),
                    "template_id": str(scope.get("template_id", "")),
                    "created_by": row.get("reviewer") or "legacy_user",
                    "metadata_json": json.dumps(scope, ensure_ascii=False),
                },
            )


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _json_object(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    try:
        payload = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}
