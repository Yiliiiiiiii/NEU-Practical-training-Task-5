from sqlalchemy import create_engine, inspect, text

from app.database import init_db


def test_init_db_upgrades_legacy_catalog_and_review_tables(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE target_schemas (
                    schema_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    schema_json TEXT NOT NULL,
                    json_schema TEXT NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO target_schemas
                VALUES ('policy_doc', 'Policy', '1.0.0', '{}', '{}', '2026-01-01')
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE review_records (
                    review_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    mapping_id TEXT NOT NULL,
                    old_target_field_id TEXT,
                    new_target_field_id TEXT,
                    decision TEXT NOT NULL,
                    comment TEXT,
                    reviewer TEXT NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO review_records
                VALUES (
                    'review_1', 'task_1', 'mapping_1', 'title', 'title',
                    'confirmed', NULL, 'legacy_user', '2026-01-01'
                )
                """
            )
        )

    init_db(bind=engine)
    init_db(bind=engine)

    inspector = inspect(engine)
    assert inspector.get_pk_constraint("target_schemas")["constrained_columns"] == [
        "record_id"
    ]
    assert "doc_id" in {
        column["name"] for column in inspector.get_columns("review_records")
    }
    with engine.connect() as connection:
        schema = connection.execute(
            text(
                "SELECT record_id, status, content_hash FROM target_schemas "
                "WHERE schema_id = 'policy_doc'"
            )
        ).one()
        review = connection.execute(
            text(
                "SELECT status, updated_at FROM review_records "
                "WHERE review_id = 'review_1'"
            )
        ).one()
    assert schema.record_id == "policy_doc:1.0.0"
    assert schema.status == "active"
    assert schema.content_hash
    assert review.status == "approved"
    assert review.updated_at is not None
