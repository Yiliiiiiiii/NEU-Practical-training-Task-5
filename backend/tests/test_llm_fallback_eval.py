import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "eval_llm_fallback_modes.py"


def load_module():
    spec = importlib.util.spec_from_file_location("eval_llm_fallback_modes", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_disabled_mode_never_calls_provider(tmp_path: Path) -> None:
    module = load_module()

    result = module.evaluate_mode("disabled", root=tmp_path)

    assert result["suggestion_count"] == 0
    assert result["auto_accepted_count"] == 0


def test_stub_suggestions_require_review_and_redact_secrets(tmp_path: Path) -> None:
    module = load_module()

    result = module.evaluate_mode("stub", root=tmp_path, secret="sk-test-secret-value")

    assert result["suggestion_count"] > 0
    assert result["review_required_count"] == result["suggestion_count"]
    assert result["auto_accepted_count"] == 0
    assert result["secret_redaction_passed"] is True
    assert "sk-test-secret-value" not in json.dumps(result)


def test_provider_error_strict_and_non_strict_modes(tmp_path: Path) -> None:
    module = load_module()

    non_strict = module.evaluate_provider_error(root=tmp_path, strict=False)
    strict = module.evaluate_provider_error(root=tmp_path, strict=True)

    assert non_strict["provider_error_count"] == 1
    assert non_strict["raised"] is False
    assert strict["provider_error_count"] == 1
    assert strict["raised"] is True


def test_badcase_blocks_adapter_call(tmp_path: Path) -> None:
    module = load_module()

    result = module.evaluate_badcase_block(root=tmp_path)

    assert result["badcase_blocked_count"] == 1
    assert result["provider_call_count"] == 0


def test_openai_compatible_requires_explicit_network_flag() -> None:
    module = load_module()

    with pytest.raises(ValueError, match="allow-network"):
        module.settings_for_mode("openai-compatible", allow_network=False)
