from pathlib import Path

import pytest
from test_downstream_exports import load_script


def test_scaffold_generates_reviewable_adapter_plugin(tmp_path: Path) -> None:
    module = load_script("scaffold_adapter")
    output = tmp_path / "enterprise_x"

    files = module.scaffold_adapter("enterprise_x", output)

    assert {path.name for path in files} >= {
        "adapter.py",
        "manifest.json",
        "README.md",
    }
    adapter = output / "adapter.py"
    source = adapter.read_text(encoding="utf-8")
    compile(source, str(adapter), "exec")
    assert "EnterpriseXAdapter" in source
    assert "enterprise_x" in source
    assert not any(
        token in source.lower()
        for token in ("api_key=", "secret=", "sk-")
    )


def test_scaffold_rejects_invalid_id_and_existing_destination(tmp_path: Path) -> None:
    module = load_script("scaffold_adapter")
    output = tmp_path / "adapter"
    module.scaffold_adapter("safe_adapter", output)

    with pytest.raises(FileExistsError):
        module.scaffold_adapter("safe_adapter", output)
    with pytest.raises(ValueError):
        module.scaffold_adapter("../unsafe", tmp_path / "unsafe")
