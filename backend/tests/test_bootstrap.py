from fastapi.testclient import TestClient


def test_health_returns_ok():
    from app.main import app

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_local_frontend_preflight():
    from app.main import create_app

    response = TestClient(create_app(init_database=False)).options(
        "/api/v1/tasks",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_create_app_initializes_database_by_default(monkeypatch):
    import app.main as main_module

    calls = []
    monkeypatch.setattr(main_module, "init_db", lambda: calls.append("called"), raising=False)

    main_module.create_app()

    assert calls == ["called"]


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
