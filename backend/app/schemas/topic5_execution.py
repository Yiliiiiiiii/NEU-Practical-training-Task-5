from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import Field, model_validator

from app.schemas.common import StrictBaseModel


class Topic5ExecutionOptions(StrictBaseModel):
    options_version: str = "1.0"
    strict_execution_options: bool = False
    mapping_mode: Literal["legacy", "global_assignment"] = "legacy"
    thresholds: dict[str, float] = Field(default_factory=dict)
    auto_accept_threshold: float | None = None
    review_threshold: float | None = None
    min_candidate_score: float = 0.45
    strict_metadata_template: bool = False
    strict_output_assertions: bool = False
    enable_llm_fallback: bool = False
    strict_llm: bool = False
    enable_mapping_repair: bool = False
    enable_lineage: bool = False
    strict_lineage: bool = False
    include_assertion_report_in_package: bool = False
    enable_legacy_transform_heuristics: bool = False
    enable_legacy_candidate_heuristics: bool = False
    provider_fallback_requires_review: bool = False
    chunk_size: int = 1200
    candidate_profile: dict[str, Any] | None = None
    negative_pairs: list[dict[str, Any]] = Field(default_factory=list)
    badcases: list[dict[str, Any]] = Field(default_factory=list)
    calibration: dict[str, Any] | None = None
    constraints: dict[str, Any] | None = None
    schema_pack_id: str | None = None
    schema_pack_version: str | None = None
    external_uir: dict[str, Any] | None = None
    no_code_schema_pack_onboarding: bool = False

    @model_validator(mode="after")
    def reject_conflicting_thresholds(self) -> Self:
        auto = self.thresholds.get("auto_accept")
        if (
            auto is not None
            and self.auto_accept_threshold is not None
            and auto != self.auto_accept_threshold
        ):
            raise ValueError("auto-accept threshold values conflict")
        review = self.thresholds.get("review_required")
        if (
            review is not None
            and self.review_threshold is not None
            and review != self.review_threshold
        ):
            raise ValueError("review threshold values conflict")
        if not 1 <= self.chunk_size <= 1_000_000:
            raise ValueError("chunk_size must be between 1 and 1000000")
        return self

    @classmethod
    def parse_legacy(
        cls, options: dict[str, Any] | None
    ) -> tuple[Topic5ExecutionOptions, list[dict[str, str]]]:
        raw = dict(options or {})
        known = set(cls.model_fields)
        unknown = sorted(str(key) for key in raw if key not in known)
        strict = bool(raw.get("strict_execution_options", False))
        if unknown and strict:
            raise ValueError(f"unknown Topic 5 execution option: {unknown[0]}")
        warnings: list[dict[str, str]] = []
        if raw:
            warnings.append(
                {
                    "code": "legacy_options_deprecated",
                    "message": (
                        "Legacy options dictionaries are accepted through contract 1.x "
                        "and will be removed in contract 2.0."
                    ),
                }
            )
        warnings.extend(
            {
                "code": "unknown_legacy_option",
                "message": f"Unknown legacy option '{name}' was rejected from execution.",
            }
            for name in unknown
        )
        payload = {key: value for key, value in raw.items() if key in known}
        return cls.model_validate(payload), warnings

    def runtime_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in self.model_dump(mode="json").items()
            if value is not None
        }
