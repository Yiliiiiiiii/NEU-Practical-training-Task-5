from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.errors import Topic5Error
from app.main import create_app
from app.schemas.mapping_template import MappingTemplate
from app.schemas.topic5_convert import Topic5ConvertRequest
from app.services.package_service import PackageBuildError
from app.services.topic5_conversion_service import Topic5ConversionService
from tests.topic5_helpers import announcement_convert_request

ROOT = Path(__file__).resolve().parents[2]


def _replay_module():
    path = ROOT / "scripts" / "replay_topic5_snapshot.py"
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_same_snapshot_replays_to_identical_semantic_hashes(tmp_path: Path) -> None:
    request = Topic5ConvertRequest.model_validate(announcement_convert_request())
    response = Topic5ConversionService(tmp_path).convert(request)
    snapshot = response.content_json
    assert "execution_snapshot" not in snapshot

    engine = _replay_module()
    source_result = Topic5ConversionService(tmp_path / "source").convert(request)
    # The pure engine snapshot is available from an explicitly constructed engine run.
    from app.schemas.topic5_execution import Topic5ExecutionOptions
    from app.services.topic5_conversion_engine import (
        ConversionEngineContext,
        Topic5ConversionEngine,
    )

    result = Topic5ConversionEngine().convert(
        uir=request.uir,
        target_schema=request.target_schema,
        metadata_template=request.metadata_template,
        mapping_rules=request.effective_mapping_template,
        content_organization=request.content_organization,
        execution_options=Topic5ExecutionOptions(
            mapping_mode="legacy", enable_llm_fallback=False
        ),
        output_assertions=request.output_assertions,
        engine_context=ConversionEngineContext(
            task_id=source_result.task_id,
            doc_id=request.uir.doc_id,
            input_mode="inline_topic5_config",
            mapping_input_name="mapping_rules",
            settings=Settings(),
        ),
    )

    report = engine.replay(result.execution_snapshot)

    assert report["status"] == "exact_match"
    assert report["semantic_match"] is True
    assert report["conversion_fingerprint_match"] is True
    assert report["engine_version_match"] is True


def test_replay_reports_schema_and_engine_version_differences(tmp_path: Path) -> None:
    request = Topic5ConvertRequest.model_validate(announcement_convert_request())
    from app.schemas.topic5_execution import Topic5ExecutionOptions
    from app.services.topic5_conversion_engine import (
        ConversionEngineContext,
        Topic5ConversionEngine,
    )

    result = Topic5ConversionEngine().convert(
        uir=request.uir,
        target_schema=request.target_schema,
        metadata_template=request.metadata_template,
        mapping_rules=request.effective_mapping_template,
        content_organization=request.content_organization,
        execution_options=Topic5ExecutionOptions(),
        output_assertions=None,
        engine_context=ConversionEngineContext(
            task_id="original",
            doc_id=request.uir.doc_id,
            input_mode="inline_topic5_config",
            mapping_input_name="mapping_rules",
            settings=Settings(),
        ),
    )
    changed_schema = copy.deepcopy(
        result.execution_snapshot["replay_contract"]["target_schema"]
    )
    changed_schema["version"] = "1.0.1"

    report = _replay_module().replay(
        result.execution_snapshot,
        target_schema_override=changed_schema,
        compare_engine_version="topic5-conversion-engine/3.0.0",
    )

    assert report["status"] == "different"
    assert report["engine_version_match"] is False
    assert "target_schema_hash" in report["conversion_differences"]


def test_resource_limit_rejects_before_candidate_extraction(tmp_path: Path) -> None:
    request = Topic5ConvertRequest.model_validate(announcement_convert_request())
    service = Topic5ConversionService(
        tmp_path,
        settings=Settings(topic5_max_uir_blocks=1),
    )

    with pytest.raises(Topic5Error) as exc_info:
        service.convert(request)

    assert exc_info.value.error_code == "too_many_uir_blocks"
    assert exc_info.value.stage == "contract"
    assert exc_info.value.path == "uir.blocks"
    assert exc_info.value.status_code == 413


def test_public_request_byte_limit_returns_structured_error_without_stack() -> None:
    app = create_app(Settings(topic5_max_request_bytes=100))
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/topic5/convert", json=announcement_convert_request()
        )

    assert response.status_code == 413
    payload = response.json()
    assert payload["error_code"] == "request_too_large"
    assert payload["stage"] == "contract"
    assert payload["path"] == "request"
    assert payload["retryable"] is False
    assert payload["trace_id"]
    assert "traceback" not in str(payload).lower()


def test_catastrophic_and_oversized_regexes_are_rejected_at_contract_time() -> None:
    payload = {
        "template_id": "safe",
        "schema_id": "safe",
        "name": "Safe",
        "version": "1.0.0",
        "regex_rules": [
            {"target_field_id": "body", "pattern": r"^(a+)+$", "group": 0}
        ],
    }
    with pytest.raises(ValidationError, match="nested repetition"):
        MappingTemplate.model_validate(payload)
    payload["regex_rules"][0]["pattern"] = "a" * 1001
    with pytest.raises(ValidationError, match="maximum length"):
        MappingTemplate.model_validate(payload)


def test_zip_limit_fails_atomically_and_leaves_no_final_package(tmp_path: Path) -> None:
    request = Topic5ConvertRequest.model_validate(announcement_convert_request())
    service = Topic5ConversionService(
        tmp_path,
        settings=Settings(topic5_max_zip_bytes=1),
    )

    with pytest.raises(PackageBuildError) as exc_info:
        service.convert(request, create_package=True)

    assert exc_info.value.stage == "zip_create"
    packages = tmp_path / "packages"
    assert not list(packages.glob("pkg_*"))
    assert not list((packages / ".tmp").glob("*"))
