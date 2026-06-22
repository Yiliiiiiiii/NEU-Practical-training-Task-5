from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SchemaPack Agent"
    storage_root: str = "storage"
    database_url: str = "sqlite:///./schemapack.db"
    llm_mode: Literal["disabled", "mock", "openai_compatible"] = "mock"
    offline_mode: bool = False
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
