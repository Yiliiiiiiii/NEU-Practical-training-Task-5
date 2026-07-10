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
        "TOPIC11_BASE_URL",
        "TOPIC11_TIMEOUT_SECONDS",
        "TOPIC11_API_KEY",
        "MAX_UPLOAD_BYTES",
        "API_KEY_AUTH_ENABLED",
        "API_KEYS",
        "AUDIT_LOG_ENABLED",
        "AUDIT_LOG_BODY_MAX_CHARS",
        "ARTIFACT_RETENTION_ENABLED",
        "ARTIFACT_RETENTION_DAYS",
        "ARTIFACT_RETENTION_DRY_RUN",
        "PACKAGE_DOWNLOAD_REQUIRES_AUTH",
        "EXTERNAL_UIR_LLM_ENABLED",
        "EXTERNAL_UIR_LLM_PROVIDER",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL",
        "DEEPSEEK_MODEL",
        "DEEPSEEK_TIMEOUT_SECONDS",
        "DEEPSEEK_MAX_RETRIES",
        "DEEPSEEK_MAX_SUGGESTIONS_PER_REQUEST",
        "DEEPSEEK_STRICT_JSON",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)
    yield
