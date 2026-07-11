from dataclasses import dataclass
from typing import Any, Literal

type ConversionStatus = Literal["failed", "review_required", "completed"]


@dataclass(frozen=True, slots=True)
class ConversionStatusInput:
    runtime_exception: bool = False
    package_write_failed: bool = False
    package_verifier_passed: bool | None = None
    metadata_passed: bool | None = None
    strict_metadata: bool = False
    assertion_error_count: int = 0
    strict_output_assertions: bool = False
    strict_provider_failed: bool = False
    mapping_review_item_count: int = 0
    unmapped_required_source_present_count: int = 0
    schema_validation_passed: bool = True
    summary_faithfulness_passed: bool | None = None
    artifact_consistency_passed: bool | None = None
    provider_fallback_used: bool = False
    provider_fallback_requires_review: bool = False


class ConversionStatusService:
    @staticmethod
    def count_required_unmapped_source_present(
        unmapped: list[dict[str, Any]],
    ) -> int:
        return sum(
            1
            for item in unmapped
            if item.get("required") is True and item.get("source_present") is True
        )

    @staticmethod
    def determine(status_input: ConversionStatusInput) -> ConversionStatus:
        if (
            status_input.runtime_exception
            or status_input.package_write_failed
            or status_input.package_verifier_passed is False
            or (status_input.metadata_passed is False and status_input.strict_metadata)
            or (
                status_input.assertion_error_count > 0
                and status_input.strict_output_assertions
            )
            or status_input.strict_provider_failed
        ):
            return "failed"

        if (
            status_input.mapping_review_item_count > 0
            or status_input.unmapped_required_source_present_count > 0
            or status_input.schema_validation_passed is False
            or status_input.metadata_passed is False
            or status_input.assertion_error_count > 0
            or status_input.summary_faithfulness_passed is False
            or status_input.artifact_consistency_passed is False
            or (
                status_input.provider_fallback_used
                and status_input.provider_fallback_requires_review
            )
        ):
            return "review_required"

        return "completed"
