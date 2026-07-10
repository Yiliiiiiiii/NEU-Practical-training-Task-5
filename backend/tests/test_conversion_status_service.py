from itertools import product

from app.services.conversion_status_service import (
    ConversionStatusInput,
    ConversionStatusService,
)


def test_conversion_status_truth_table_is_exhaustive() -> None:
    for values in product((False, True), repeat=15):
        (
            runtime_exception,
            package_write_failed,
            package_verifier_failed,
            metadata_failed,
            strict_metadata,
            assertion_error,
            strict_assertions,
            strict_provider_failed,
            mapping_review,
            unmapped_required,
            schema_validation_failed,
            summary_faithfulness_failed,
            artifact_consistency_failed,
            provider_fallback_used,
            provider_fallback_requires_review,
        ) = values
        status_input = ConversionStatusInput(
            runtime_exception=runtime_exception,
            package_write_failed=package_write_failed,
            package_verifier_passed=not package_verifier_failed,
            metadata_passed=not metadata_failed,
            strict_metadata=strict_metadata,
            assertion_error_count=int(assertion_error),
            strict_output_assertions=strict_assertions,
            strict_provider_failed=strict_provider_failed,
            mapping_review_item_count=int(mapping_review),
            unmapped_required_source_present_count=int(unmapped_required),
            schema_validation_passed=not schema_validation_failed,
            summary_faithfulness_passed=not summary_faithfulness_failed,
            artifact_consistency_passed=not artifact_consistency_failed,
            provider_fallback_used=provider_fallback_used,
            provider_fallback_requires_review=provider_fallback_requires_review,
        )

        has_failure = (
            runtime_exception
            or package_write_failed
            or package_verifier_failed
            or (metadata_failed and strict_metadata)
            or (assertion_error and strict_assertions)
            or strict_provider_failed
        )
        has_review = (
            mapping_review
            or unmapped_required
            or schema_validation_failed
            or metadata_failed
            or assertion_error
            or summary_faithfulness_failed
            or artifact_consistency_failed
            or (provider_fallback_used and provider_fallback_requires_review)
        )
        expected = "failed" if has_failure else "review_required" if has_review else "completed"

        assert ConversionStatusService.determine(status_input) == expected


def test_absent_optional_checks_do_not_prevent_completion() -> None:
    status_input = ConversionStatusInput(
        package_verifier_passed=None,
        metadata_passed=None,
        summary_faithfulness_passed=None,
        artifact_consistency_passed=None,
    )

    assert ConversionStatusService.determine(status_input) == "completed"
