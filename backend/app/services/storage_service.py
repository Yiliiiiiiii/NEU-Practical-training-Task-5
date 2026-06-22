import hashlib
import json
from pathlib import Path
from typing import Any


class StorageService:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative_path: str | Path) -> Path:
        path = Path(relative_path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("unsafe storage path")

        resolved = (self.root / path).resolve()
        if self.root != resolved and self.root not in resolved.parents:
            raise ValueError("unsafe storage path")
        return resolved

    def save_json(self, relative_path: str | Path, data: Any) -> Path:
        path = self.resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return path

    def read_json(self, relative_path: str | Path) -> Any:
        return json.loads(self.resolve(relative_path).read_text(encoding="utf-8"))

    def write_text(self, relative_path: str | Path, text: str) -> Path:
        path = self.resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def read_text(self, relative_path: str | Path) -> str:
        return self.resolve(relative_path).read_text(encoding="utf-8")

    def sha256(self, relative_path: str | Path) -> str:
        digest = hashlib.sha256()
        with self.resolve(relative_path).open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
