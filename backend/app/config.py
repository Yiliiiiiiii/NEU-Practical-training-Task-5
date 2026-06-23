from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SchemaPack Agent"
    storage_root: str = "storage"
    database_url: str = "sqlite:///./schemapack.db"
    llm_mode: Literal["disabled", "mock", "openai_compatible"] = "mock"
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "schema-mapping-model"
    llm_prompt_version: str = "mapping-v1"
    llm_timeout_seconds: float = Field(default=30.0, gt=0)
    offline_mode: bool = False
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
    cors_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]
