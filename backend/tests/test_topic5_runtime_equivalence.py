from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import Settings
from app.schemas.content_organization import ContentOrganizationOptions
from app.schemas.mapping_template import MappingTemplate
from app.schemas.target_schema import TargetSchema
from app.schemas.topic5_convert import Topic5ConvertRequest
from app.schemas.topic5_execution import Topic5ExecutionOptions
from app.schemas.uir import UIRDocument
from app.services.topic5_conversion_engine import (
    ConversionEngineContext,
    Topic5ConversionEngine,
)

ROOT = Path(__file__).resolve().parents[2]


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _case(name: str):
    if name in {"announcement_doc", "event_notice_doc"}:
        request = Topic5ConvertRequest.model_validate(
            _json(
                ROOT
                / "examples"
                / "topic5_inline"
                / (
                    "announcement_convert_request.json"
                    if name == "announcement_doc"
                    else "event_notice_convert_request.json"
                )
            )
        )
        return (
            request.uir,
            request.target_schema,
            request.effective_mapping_template,
            request.content_organization,
            request.metadata_template,
        )
    family = name.removesuffix("_doc")
    uir_path = next(
        iter(sorted((ROOT / "examples" / "production_like" / "uir" / family).glob("*.json")))
    )
    return (
        UIRDocument.model_validate(_json(uir_path)),
        TargetSchema.model_validate(
            _json(ROOT / "examples" / "production_like" / "schemas" / f"{name}_v1.json")
        ),
        MappingTemplate.model_validate(
            _json(
                ROOT
                / "examples"
                / "production_like"
                / "mapping_templates"
                / f"{name}_base_v1.json"
            )
        ),
        ContentOrganizationOptions(),
        None,
    )


@pytest.mark.parametrize(
    "schema_id",
    [
        "announcement_doc",
        "event_notice_doc",
        "general_doc",
        "meeting_doc",
        "policy_doc",
    ],
)
def test_inline_and_registered_contexts_have_identical_semantic_hashes(
    schema_id: str,
) -> None:
    uir, schema, mapping, content_org, metadata = _case(schema_id)
    options = Topic5ExecutionOptions(
        mapping_mode="legacy",
        enable_llm_fallback=False,
        enable_legacy_candidate_heuristics=False,
    )
    engine = Topic5ConversionEngine()

    inline = engine.convert(
        uir=uir,
        target_schema=schema,
        metadata_template=metadata,
        mapping_rules=mapping,
        content_organization=content_org,
        execution_options=options,
        output_assertions=None,
        engine_context=ConversionEngineContext(
            task_id="inline-operation-id",
            doc_id=uir.doc_id,
            input_mode="inline_topic5_config",
            mapping_input_name="mapping_rules",
            settings=Settings(),
        ),
    )
    registered = engine.convert(
        uir=uir,
        target_schema=schema,
        metadata_template=metadata,
        mapping_rules=mapping,
        content_organization=content_org,
        execution_options=options,
        output_assertions=None,
        engine_context=ConversionEngineContext(
            task_id="registered-operation-id",
            doc_id=uir.doc_id,
            input_mode="registered_task",
            mapping_input_name="mapping_rules",
            settings=Settings(),
        ),
    )

    assert inline.conversion_fingerprints == registered.conversion_fingerprints
    assert inline.semantic_artifact_hashes == registered.semantic_artifact_hashes
