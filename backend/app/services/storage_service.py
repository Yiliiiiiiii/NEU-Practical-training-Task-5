import hashlib
import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

_WRITE_LOCKS_GUARD = threading.Lock()
_WRITE_LOCKS: dict[str, threading.RLock] = {}


def _write_lock(path: Path) -> threading.RLock:
    key = os.path.normcase(os.path.normpath(str(path)))
    with _WRITE_LOCKS_GUARD:
        return _WRITE_LOCKS.setdefault(key, threading.RLock())


class StorageService:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative_path: str | Path) -> Path:
        path = Path(relative_path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("unsafe storage path")

        resolved = (self.root / path).resolve()
        resolved = self._without_extended_prefix(resolved)
        root_key = os.path.normcase(os.path.normpath(str(self.root)))
        resolved_key = os.path.normcase(os.path.normpath(str(resolved)))
        if os.path.commonpath([root_key, resolved_key]) != root_key:
            raise ValueError("unsafe storage path")
        return resolved

    def save_json(self, relative_path: str | Path, data: Any) -> Path:
        path = self.resolve(relative_path)
        return self._atomic_write(
            path,
            json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        )

    def read_json(self, relative_path: str | Path) -> Any:
        return json.loads(self.resolve(relative_path).read_text(encoding="utf-8"))

    def write_text(self, relative_path: str | Path, text: str) -> Path:
        path = self.resolve(relative_path)
        return self._atomic_write(path, text)

    @staticmethod
    def _without_extended_prefix(path: Path) -> Path:
        value = str(path)
        if value.startswith("\\\\?\\"):
            value = value[4:]
        return Path(value)

    @staticmethod
    def _atomic_write(path: Path, text: str) -> Path:
        with _write_lock(path):
            path.parent.mkdir(parents=True, exist_ok=True)
            temp_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    delete=False,
                    dir=path.parent,
                    prefix=f".{path.name}.",
                    suffix=".tmp",
                ) as temp_file:
                    temp_file.write(text)
                    temp_file.flush()
                    os.fsync(temp_file.fileno())
                    temp_path = Path(temp_file.name)
                temp_path.replace(path)
            finally:
                if temp_path is not None:
                    temp_path.unlink(missing_ok=True)
        return path

    def read_text(self, relative_path: str | Path) -> str:
        return self.resolve(relative_path).read_text(encoding="utf-8")

    def sha256(self, relative_path: str | Path) -> str:
        digest = hashlib.sha256()
        with self.resolve(relative_path).open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
