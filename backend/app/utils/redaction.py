from typing import Any

REDACTED = "[REDACTED]"
SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "deepseek_api_key",
    "llm_api_key",
    "password",
    "secret",
    "token",
}
SENSITIVE_SUFFIXES = ("_api_key", "_password", "_secret", "_token")


def redact_sensitive_values(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: REDACTED if _is_sensitive_key(str(key)) else redact_sensitive_values(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive_values(item) for item in value]
    if isinstance(value, tuple):
        return [redact_sensitive_values(item) for item in value]
    return value


def _is_sensitive_key(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    return normalized in SENSITIVE_KEYS or normalized.endswith(SENSITIVE_SUFFIXES)
