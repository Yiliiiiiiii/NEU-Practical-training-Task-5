from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load(script_name: str) -> ModuleType:
    path = ROOT / "scripts" / script_name
    scripts = str(path.parent)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location(f"test_{script_name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "script_name",
    ["eval_topic5_mapping_v2.py", "eval_topic5_tag_quality_v2.py"],
)
def test_frozen_hashes_normalize_text_line_endings(
    tmp_path: Path, script_name: str
) -> None:
    path = tmp_path / "fixture.json"
    path.write_bytes(b'{"key": "value"}\r\n')
    crlf_digest = _load(script_name)._sha256(path)

    path.write_bytes(b'{"key": "value"}\n')

    assert _load(script_name)._sha256(path) == crlf_digest
