from fastapi.testclient import TestClient


def test_health_returns_ok():
    from app.main import app

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_settings_defaults_are_safe():
    from app.config import Settings

    settings = Settings()

    assert settings.app_name == "SchemaPack Agent"
    assert settings.storage_root == "storage"
    assert settings.database_url == "sqlite:///./schemapack.db"
    assert settings.llm_mode == "mock"
    assert settings.offline_mode is False
    assert settings.max_upload_bytes == 10 * 1024 * 1024


def test_settings_support_environment_overrides(monkeypatch):
    from app.config import Settings

    monkeypatch.setenv("STORAGE_ROOT", "runtime-storage")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("LLM_MODE", "disabled")
    monkeypatch.setenv("OFFLINE_MODE", "true")
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "1024")

    settings = Settings()

    assert settings.storage_root == "runtime-storage"
    assert settings.database_url == "sqlite:///./test.db"
    assert settings.llm_mode == "disabled"
    assert settings.offline_mode is True
    assert settings.max_upload_bytes == 1024


def test_database_metadata_declares_mvp_tables():
    from app.db.models import Base

    expected_tables = {
        "documents",
        "conversion_tasks",
        "target_schemas",
        "mapping_templates",
        "field_candidates",
        "field_mappings",
        "transform_traces",
        "canonical_models",
        "validation_reports",
        "consistency_reports",
        "output_packages",
        "package_files",
        "review_records",
    }

    assert expected_tables.issubset(set(Base.metadata.tables))
