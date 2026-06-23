from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def clear_settings_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    keys = [
        "APP_NAME",
        "STORAGE_ROOT",
        "DATABASE_URL",
        "LLM_MODE",
        "LLM_BASE_URL",
        "LLM_API_KEY",
        "LLM_MODEL",
        "LLM_PROMPT_VERSION",
        "LLM_TIMEOUT_SECONDS",
        "OFFLINE_MODE",
        "MAX_UPLOAD_BYTES",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)
    yield
