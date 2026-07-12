from __future__ import annotations

import re
from typing import Any

from app.config import Settings
from app.errors import Topic5Error
from app.schemas.mapping_template import MappingTemplate
from app.schemas.target_schema import TargetSchema
from app.schemas.uir import UIRDocument
from app.services.conversion_fingerprint_service import ConversionFingerprintService
from app.utils.regex_safety import validate_safe_regex


class Topic5ResourceLimitService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def validate_input(
        self,
        *,
        uir: UIRDocument,
        target_schema: TargetSchema,
        mapping_rules: MappingTemplate,
        runtime_options: dict[str, Any],
    ) -> None:
        request_bytes = len(
            ConversionFingerprintService.canonical_bytes(
                {
                    "uir": uir,
                    "target_schema": target_schema,
                    "mapping_rules": mapping_rules,
                    "execution_options": runtime_options,
                }
            )
        )
        self._maximum(
            "request_too_large",
            "request",
            request_bytes,
            self.settings.topic5_max_request_bytes,
        )
        self._maximum(
            "too_many_uir_blocks",
            "uir.blocks",
            len(uir.blocks),
            self.settings.topic5_max_uir_blocks,
        )
        for index, block in enumerate(uir.blocks):
            self._maximum(
                "block_text_too_large",
                f"uir.blocks[{index}].text",
                len(block.text or ""),
                self.settings.topic5_max_block_text_characters,
            )
        self._maximum(
            "too_many_assets",
            "uir.assets",
            len(uir.assets),
            self.settings.topic5_max_assets,
        )
        self._maximum(
            "too_many_entities",
            "uir.entities",
            len(uir.entities),
            self.settings.topic5_max_entities,
        )
        self._maximum(
            "too_many_target_fields",
            "target_schema.fields",
            len(target_schema.fields),
            self.settings.topic5_max_target_fields,
        )
        mapping_rule_count = (
            sum(len(items) for items in mapping_rules.aliases.values())
            + len(mapping_rules.regex_rules)
            + len(mapping_rules.transform_rules)
            + len(mapping_rules.defaults)
            + len(mapping_rules.enum_maps)
        )
        self._maximum(
            "too_many_mapping_rules",
            "mapping_rules",
            mapping_rule_count,
            self.settings.topic5_max_mapping_rules,
        )
        for index, rule in enumerate(mapping_rules.regex_rules):
            self._validate_regex(
                rule.pattern, f"mapping_rules.regex_rules[{index}].pattern"
            )
        for index, item in enumerate(runtime_options.get("negative_pairs", [])):
            pattern = item.get("source_pattern") if isinstance(item, dict) else None
            if isinstance(pattern, str):
                self._validate_regex(
                    pattern, f"execution_options.negative_pairs[{index}].source_pattern"
                )

    def validate_output(self, *, rendered: Any) -> None:
        self._maximum(
            "too_many_chunks",
            "output.chunks",
            len(rendered.chunks),
            self.settings.topic5_max_chunks,
            stage="content_organization",
        )
        output_bytes = len(
            ConversionFingerprintService.canonical_bytes(
                {
                    "content_json": rendered.structured_json,
                    "content_markdown": rendered.markdown,
                    "chunks": rendered.chunks,
                }
            )
        )
        self._maximum(
            "output_too_large",
            "output",
            output_bytes,
            self.settings.topic5_max_output_bytes,
            stage="render",
        )

    def _validate_regex(self, pattern: str, path: str) -> None:
        try:
            validate_safe_regex(
                pattern, max_length=self.settings.topic5_max_regex_length
            )
        except (ValueError, re.error) as exc:
            raise Topic5Error(
                error_code="unsafe_regex",
                stage="contract",
                path=path,
                message=str(exc),
                details={"max_length": self.settings.topic5_max_regex_length},
            ) from exc

    @staticmethod
    def _maximum(
        error_code: str,
        path: str,
        actual: int,
        maximum: int,
        *,
        stage: str = "contract",
    ) -> None:
        if actual <= maximum:
            return
        raise Topic5Error(
            error_code=error_code,
            stage=stage,
            path=path,
            message=f"resource limit exceeded at {path}",
            details={"actual": actual, "maximum": maximum},
            status_code=413,
        )
