from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel


class ConversionFingerprintService:
    ENGINE_VERSION = "topic5-conversion-engine/2.0.0"
    OPERATIONAL_KEYS = {
        "task_id",
        "package_id",
        "created_at",
        "started_at",
        "finished_at",
        "duration",
        "duration_ms",
        "absolute_path",
        "zip_path",
        "mapping_id",
        "candidate_id",
        "review_id",
        "chunk_id",
        "source_chunk_ids",
        "input_mode",
        "mapping_input_name",
        "execution_option_warnings",
    }

    @classmethod
    def canonical_bytes(cls, value: Any, *, semantic: bool = False) -> bytes:
        normalized = cls._normalize(value, semantic=semantic)
        return json.dumps(
            normalized,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    @classmethod
    def hash_value(cls, value: Any, *, semantic: bool = False) -> str:
        return hashlib.sha256(cls.canonical_bytes(value, semantic=semantic)).hexdigest()

    @classmethod
    def conversion_fingerprints(
        cls,
        *,
        uir: Any,
        target_schema: Any,
        metadata_template: Any,
        mapping_rules: Any,
        content_organization: Any,
        execution_options: Any,
    ) -> dict[str, str]:
        components = {
            "input_uir_hash": cls.hash_value(uir, semantic=True),
            "target_schema_hash": cls.hash_value(target_schema, semantic=True),
            "metadata_template_hash": cls.hash_value(
                metadata_template, semantic=True
            ),
            "mapping_rules_hash": cls.hash_value(mapping_rules, semantic=True),
            "content_organization_hash": cls.hash_value(
                content_organization, semantic=True
            ),
            "execution_options_hash": cls.hash_value(
                execution_options, semantic=True
            ),
            "engine_version": cls.ENGINE_VERSION,
        }
        components["conversion_fingerprint"] = cls.hash_value(components)
        return components

    @classmethod
    def semantic_artifact_hashes(
        cls,
        *,
        data: Any,
        document_metadata: Any,
        document_summary: Any,
        canonical_blocks: Any,
        chunks: Any,
        tag_traces: Any,
        entity_tags: Any,
        reports: Any | None = None,
    ) -> dict[str, str]:
        values = {
            "structured_data": data,
            "document_metadata": document_metadata,
            "document_summary": document_summary,
            "canonical_blocks": canonical_blocks,
            "chunks": chunks,
            "tag_traces": tag_traces,
            "entity_tags": entity_tags,
            "reports": reports or {},
        }
        hashes = {
            name: cls.hash_value(value, semantic=True)
            for name, value in values.items()
        }
        hashes["semantic_package_fingerprint"] = cls.hash_value(hashes)
        return hashes

    @classmethod
    def _normalize(cls, value: Any, *, semantic: bool) -> Any:
        if isinstance(value, BaseModel):
            value = value.model_dump(mode="json")
        if isinstance(value, dict):
            return {
                str(key): cls._normalize(item, semantic=semantic)
                for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
                if not semantic or str(key) not in cls.OPERATIONAL_KEYS
            }
        if isinstance(value, list | tuple):
            return [cls._normalize(item, semantic=semantic) for item in value]
        if isinstance(value, str):
            return value.replace("\r\n", "\n").replace("\r", "\n")
        return value
