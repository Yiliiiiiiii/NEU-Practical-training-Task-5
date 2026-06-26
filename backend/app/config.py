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
    llm_timeout_seconds: float = Field(default=8.0, ge=0.1)
    offline_mode: bool = False
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
