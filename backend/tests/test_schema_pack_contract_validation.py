from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run_validator(pack_dir: Path) -> dict:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_schema_pack.py"), str(pack_dir)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_validate_announcement_schema_pack_passes():
    result = _run_validator(ROOT / "schema_packs" / "examples" / "announcement_doc")

    assert result["status"] == "passed"
    assert result["errors"] == []


def test_validate_event_notice_schema_pack_passes():
    result = _run_validator(ROOT / "schema_packs" / "examples" / "event_notice_doc")

    assert result["status"] == "passed"
    assert result["errors"] == []


def test_validate_schema_pack_fails_on_missing_mapping_rules(tmp_path):
    source = ROOT / "schema_packs" / "examples" / "announcement_doc"
    pack = tmp_path / "announcement_doc"
    shutil.copytree(source, pack)
    (pack / "mapping_rules.yaml").unlink()

    result = _run_validator(pack)

    assert result["status"] == "failed"
    assert "mapping_rules.yaml is missing" in result["errors"]
