"""Replay a Topic 5 execution snapshot and compare semantic fingerprints."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.config import Settings  # noqa: E402
from app.errors import Topic5Error  # noqa: E402
from app.schemas.content_organization import ContentOrganizationOptions  # noqa: E402
from app.schemas.conversion_assertions import ConversionAssertionConfig  # noqa: E402
from app.schemas.mapping_template import MappingTemplate  # noqa: E402
from app.schemas.metadata_template import MetadataTemplateConfig  # noqa: E402
from app.schemas.target_schema import TargetSchema  # noqa: E402
from app.schemas.topic5_execution import Topic5ExecutionOptions  # noqa: E402
from app.schemas.uir import UIRDocument  # noqa: E402
from app.services.conversion_fingerprint_service import (  # noqa: E402
    ConversionFingerprintService,
)
from app.services.topic5_conversion_engine import (  # noqa: E402
    ConversionEngineContext,
    Topic5ConversionEngine,
)


def load_snapshot(
    *, snapshot_path: Path | None, task_id: str | None, storage_root: Path
) -> tuple[Path, dict[str, Any]]:
    if snapshot_path is None:
        if task_id is None or not re.fullmatch(r"[A-Za-z0-9_.-]+", task_id):
            raise Topic5Error(
                error_code="invalid_replay_task_id",
                stage="replay",
                path="task_id",
                message="task ID is required and must be path-safe",
            )
        snapshot_path = storage_root / "tasks" / task_id / "execution_snapshot.json"
    resolved = snapshot_path.resolve()
    if not resolved.is_file():
        raise Topic5Error(
            error_code="replay_snapshot_missing",
            stage="replay",
            path=str(snapshot_path),
            message="execution snapshot does not exist",
        )
    value = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Topic5Error(
            error_code="invalid_replay_snapshot",
            stage="replay",
            path=str(snapshot_path),
            message="execution snapshot must contain an object",
        )
    return resolved, value


def replay(
    snapshot: dict[str, Any],
    *,
    target_schema_override: dict[str, Any] | None = None,
    compare_engine_version: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    contract = snapshot.get("replay_contract")
    if snapshot.get("replay_contract_version") != "1.0" or not isinstance(
        contract, dict
    ):
        raise Topic5Error(
            error_code="replay_contract_missing",
            stage="replay",
            path="replay_contract",
            message="snapshot does not contain replay contract 1.0",
        )
    target_schema_payload = target_schema_override or contract["target_schema"]
    metadata_payload = contract.get("metadata_template")
    assertion_payload = contract.get("output_assertions")
    uir = UIRDocument.model_validate(contract["uir"])
    target_schema = TargetSchema.model_validate(target_schema_payload)
    mapping_rules = MappingTemplate.model_validate(contract["mapping_rules"])
    execution_options = Topic5ExecutionOptions.model_validate(
        contract["execution_options"]
    )
    result = Topic5ConversionEngine().convert(
        uir=uir,
        target_schema=target_schema,
        metadata_template=(
            MetadataTemplateConfig.model_validate(metadata_payload)
            if metadata_payload is not None
            else None
        ),
        mapping_rules=mapping_rules,
        content_organization=ContentOrganizationOptions.model_validate(
            contract["content_organization"]
        ),
        execution_options=execution_options,
        output_assertions=(
            ConversionAssertionConfig.model_validate(assertion_payload)
            if assertion_payload is not None
            else None
        ),
        engine_context=ConversionEngineContext(
            task_id=f"replay-{snapshot.get('task_id', 'snapshot')}",
            doc_id=uir.doc_id,
            input_mode="replay",
            mapping_input_name="mapping_rules",
            settings=settings or Settings(),
        ),
    )
    baseline_semantic = snapshot.get("semantic_artifact_hashes", {})
    semantic_differences = {
        name: {
            "before": baseline_semantic.get(name),
            "after": result.semantic_artifact_hashes.get(name),
        }
        for name in sorted(
            set(baseline_semantic) | set(result.semantic_artifact_hashes)
        )
        if baseline_semantic.get(name) != result.semantic_artifact_hashes.get(name)
    }
    baseline_conversion = snapshot.get("conversion_fingerprints", {})
    conversion_differences = {
        name: {
            "before": baseline_conversion.get(name),
            "after": result.conversion_fingerprints.get(name),
        }
        for name in sorted(
            set(baseline_conversion) | set(result.conversion_fingerprints)
        )
        if baseline_conversion.get(name) != result.conversion_fingerprints.get(name)
    }
    baseline_engine = str(snapshot.get("engine_version") or "unknown")
    compared_engine = compare_engine_version or ConversionFingerprintService.ENGINE_VERSION
    engine_version_changed = baseline_engine != compared_engine
    exact = not semantic_differences and not conversion_differences and not engine_version_changed
    return {
        "status": "exact_match" if exact else "different",
        "semantic_match": not semantic_differences,
        "conversion_fingerprint_match": not conversion_differences,
        "engine_version_match": not engine_version_changed,
        "engine_version": {
            "before": baseline_engine,
            "after": compared_engine,
        },
        "semantic_differences": semantic_differences,
        "conversion_differences": conversion_differences,
        "replay_conversion_fingerprints": result.conversion_fingerprints,
        "replay_semantic_artifact_hashes": result.semantic_artifact_hashes,
        "claim_boundary": "Topic 5 deterministic replay without package or scheduler mutation",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--snapshot", type=Path)
    source.add_argument("--task-id")
    parser.add_argument("--storage-root", type=Path, default=ROOT / "storage")
    parser.add_argument("--target-schema", type=Path)
    parser.add_argument("--compare-engine-version")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        snapshot_path, snapshot = load_snapshot(
            snapshot_path=args.snapshot,
            task_id=args.task_id,
            storage_root=args.storage_root,
        )
        schema_override = (
            json.loads(args.target_schema.read_text(encoding="utf-8"))
            if args.target_schema
            else None
        )
        report = {
            "snapshot_path": str(snapshot_path),
            **replay(
                snapshot,
                target_schema_override=schema_override,
                compare_engine_version=args.compare_engine_version,
            ),
        }
        exit_code = 0
    except Topic5Error as exc:
        report = {"status": "failed", "error": exc.to_dict()}
        exit_code = 2
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
