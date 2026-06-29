from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def clear_settings_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    keys = [
        "APP_NAME",
        "APP_ENV",
        "STORAGE_ROOT",
        "DATABASE_URL",
        "LLM_MODE",
        "LLM_FALLBACK_ENABLED",
        "LLM_BASE_URL",
        "LLM_API_KEY",
        "LLM_MODEL",
        "LLM_TIMEOUT_SECONDS",
        "OFFLINE_MODE",
        "MAX_UPLOAD_BYTES",
        "API_KEY_AUTH_ENABLED",
        "API_KEYS",
        "AUDIT_LOG_ENABLED",
        "AUDIT_LOG_BODY_MAX_CHARS",
        "ARTIFACT_RETENTION_ENABLED",
        "ARTIFACT_RETENTION_DAYS",
        "ARTIFACT_RETENTION_DRY_RUN",
        "PACKAGE_DOWNLOAD_REQUIRES_AUTH",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)
    yield
