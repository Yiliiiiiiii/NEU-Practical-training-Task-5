from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SchemaPack Agent"
    app_env: Literal["development", "test", "production"] = "development"
    storage_root: str = "storage"
    database_url: str = "sqlite:///./schemapack.db"
    llm_mode: Literal["disabled", "mock", "openai_compatible"] = "mock"
    llm_fallback_enabled: bool = False
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = Field(default=20.0, ge=0.1)
    llm_max_retries: int = Field(default=0, ge=0, le=5)
    llm_max_suggestions_per_task: int = Field(default=20, ge=0)
    llm_strict_failure: bool = False
    external_uir_llm_enabled: bool = False
    external_uir_llm_provider: str = "deepseek"
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_timeout_seconds: int = Field(default=20, ge=1)
    deepseek_max_retries: int = Field(default=0, ge=0, le=5)
    deepseek_max_suggestions_per_request: int = Field(default=20, ge=0)
    deepseek_strict_json: bool = True
    offline_mode: bool = False
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
    api_key_auth_enabled: bool = False
    api_keys: str = ""
    audit_log_enabled: bool = True
    audit_log_body_max_chars: int = Field(default=2000, ge=0)
    artifact_retention_enabled: bool = False
    artifact_retention_days: int = Field(default=30, ge=1)
    artifact_retention_dry_run: bool = True
    package_download_requires_auth: bool = True
