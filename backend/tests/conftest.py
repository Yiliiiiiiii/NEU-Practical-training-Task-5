from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def clear_settings_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    keys = [
        "APP_NAME",
        "STORAGE_ROOT",
        "DATABASE_URL",
        "LLM_MODE",
        "OFFLINE_MODE",
        "MAX_UPLOAD_BYTES",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)
    yield
