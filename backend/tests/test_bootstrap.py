from fastapi.testclient import TestClient


def test_health_returns_ok():
    from app.main import app

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_app_startup_initializes_database(monkeypatch):
    from app import main

    calls = []
    monkeypatch.setattr(main, "init_db", lambda: calls.append("init"))

    with TestClient(main.create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert calls == ["init"]


def test_settings_defaults_are_safe():
    from app.config import Settings

    settings = Settings(_env_file=None)

    assert settings.app_name == "SchemaPack Agent"
    assert settings.app_env == "development"
    assert settings.storage_root == "storage"
    assert settings.database_url == "sqlite:///./schemapack.db"
    assert settings.llm_mode == "mock"
    assert settings.llm_fallback_enabled is False
    assert settings.llm_base_url == ""
    assert settings.llm_api_key == ""
    assert settings.llm_model == "gpt-4o-mini"
    assert settings.llm_timeout_seconds == 20.0
    assert settings.llm_max_retries == 0
    assert settings.llm_max_suggestions_per_task == 20
    assert settings.llm_strict_failure is False
    assert settings.offline_mode is False
    assert settings.max_upload_bytes == 10 * 1024 * 1024


def test_settings_support_environment_overrides(monkeypatch):
    from app.config import Settings

    monkeypatch.setenv("STORAGE_ROOT", "runtime-storage")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("LLM_MODE", "disabled")
    monkeypatch.setenv("LLM_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("LLM_BASE_URL", "https://llm.example/v1")
    monkeypatch.setenv("LLM_API_KEY", "secret")
    monkeypatch.setenv("LLM_MODEL", "demo-model")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "2.5")
    monkeypatch.setenv("OFFLINE_MODE", "true")
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "1024")

    settings = Settings()

    assert settings.app_env == "production"
    assert settings.storage_root == "runtime-storage"
    assert settings.database_url == "sqlite:///./test.db"
    assert settings.llm_mode == "disabled"
    assert settings.llm_fallback_enabled is True
    assert settings.llm_base_url == "https://llm.example/v1"
    assert settings.llm_api_key == "secret"
    assert settings.llm_model == "demo-model"
    assert settings.llm_timeout_seconds == 2.5
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
        "knowledge_candidates",
        "knowledge_packs",
        "knowledge_pack_items",
    }

    assert expected_tables.issubset(set(Base.metadata.tables))
