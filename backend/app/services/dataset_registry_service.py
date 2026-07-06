import json
from pathlib import Path

from app.schemas.evaluation_center import DatasetRegistryItem


class DatasetRegistryService:
    def __init__(self, registry_path: str | Path) -> None:
        self.registry_path = Path(registry_path)

    def list_datasets(self) -> list[DatasetRegistryItem]:
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        items = payload.get("items", []) if isinstance(payload, dict) else []
        return [DatasetRegistryItem.model_validate(item) for item in items]
