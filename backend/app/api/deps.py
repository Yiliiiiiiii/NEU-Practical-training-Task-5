from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.session import SessionLocal
from app.services.storage_service import StorageService


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_settings() -> Settings:
    return Settings()


def get_storage_service(settings: Annotated[Settings, Depends(get_settings)]) -> StorageService:
    return StorageService(settings.storage_root)
