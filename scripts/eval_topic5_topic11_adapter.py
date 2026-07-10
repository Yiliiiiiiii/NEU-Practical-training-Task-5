"""Evaluate offline Topic 11 adapter fallback, safety, and legacy compatibility."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import httpx


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for import_path in (ROOT, BACKEND):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from app.config import Settings  # noqa: E402
from app.schemas.canonical import CanonicalModel  # noqa: E402
from app.schemas.chunk_provider import ChunkProviderResponse  # noqa: E402
from app.schemas.content_organization import ContentOrganizationOptions  # noqa: E402
from app.services.chunk_providers.base import (  # noqa: E402
    ChunkProviderError,
    ChunkProviderInvocation,
)
from app.services.chunk_providers.resolver import ChunkProviderResolver  # noqa: E402
from app.services.chunk_providers.topic11_http import Topic11HttpChunkProvider  # noqa: E402
from scripts.topic5_eval_common import (  # noqa: E402
    build_case_report,
    load_case_fixture,
    write_json_report,
)


DEFAULT_FIXTURE = ROOT / "eval" / "topic5_topic11_adapter" / "v2" / "cases.json"
DEFAULT_OUTPUT = ROOT / "reports" / "topic5_batch_2" / "topic11_adapter.json"
DATASET_ID = "topic5_topic11_adapter"


class FixtureProvider:
    def __init__(
        self,
        *,
        response: ChunkProviderResponse | None = None,
        error_code: str | None = None,
    ) -> None:
        self.response = response
        self.error_code = error_code

    def provide(self, _request) -> ChunkProviderInvocation:
        if self.error_code:
            raise ChunkProviderError(self.error_code)
        if self.response is None:
            raise AssertionError("fixture provider requires a response or error")
        return ChunkProviderInvocation(response=self.response, latency_ms=1)


def load_fixture(path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    fixture = load_case_fixture(path, dataset_id=DATASET_ID)
    if not isinstance(fixture.get("base"), dict):
        raise ValueError("Topic 11 fixture requires base canonical and legacy chunks")
    return fixture


def _options() -> ContentOrganizationOptions:
    return ContentOrganizationOptions.model_validate(
        {
            "provider": "topic11",
            "fallback_to_internal": True,
            "strict_provider": False,
            "chunk_strategy": "source_block_aware",
            "target_tokens": 128,
            "min_tokens": 1,
            "max_tokens": 256,
            "overlap_tokens": 0,
        }
    )


def _response(chunks: list[dict[str, Any]]) -> ChunkProviderResponse:
    return ChunkProviderResponse.model_validate(
        {
            "contract_version": "1.0",
            "provider": "topic11",
            "provider_version": "fixture-v2",
            "chunks": chunks,
            "warnings": [],
            "trace": {},
        }
    )


def evaluate_case(case: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    canonical = CanonicalModel.model_validate(base["canonical"])
    legacy_chunks = base["legacy_chunks"]
    secret = str(case.get("secret") or "")
    client: httpx.Client | None = None

    if case["category"] == "legacy":
        resolver = ChunkProviderResolver(settings=Settings(offline_mode=True))
        result = resolver.resolve(
            canonical=canonical,
            options=None,
            legacy_chunks=legacy_chunks,
        )
        legacy_compatible = result.chunks == legacy_chunks
        return {
            "case_id": case["case_id"],
            "category": case["category"],
            "passed": legacy_compatible,
            "legacy_compatible": legacy_compatible,
            "fallback_succeeded": None,
            "invalid_output_accepted": False,
            "secret_leaked": False,
            "trace": result.trace.model_dump(mode="json"),
        }

    if case["category"] == "secret":
        settings = Settings(
            topic11_base_url="https://topic11.invalid",
            topic11_api_key=secret,
        )

        def timeout_handler(_request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout(secret)

        client = httpx.Client(transport=httpx.MockTransport(timeout_handler))
        provider = Topic11HttpChunkProvider(settings, client=client)
    elif case["category"] == "invalid":
        settings = Settings()
        provider = FixtureProvider(response=_response(case["chunks"]))
    else:
        settings = Settings()
        provider = FixtureProvider(error_code=case["error_code"])

    try:
        result = ChunkProviderResolver(
            settings=settings,
            external_provider=provider,
        ).resolve(
            canonical=canonical,
            options=_options(),
            legacy_chunks=legacy_chunks,
        )
    finally:
        if client is not None:
            client.close()

    trace = result.trace.model_dump(mode="json")
    fallback_succeeded = (
        trace["fallback_used"] is True
        and trace["used_provider"] == "internal"
        and trace["fallback_reason"] == case["expected_fallback_reason"]
    )
    invalid_output_accepted = (
        case["category"] == "invalid" and trace["used_provider"] == "topic11"
    )
    serialized = json.dumps(
        {"trace": trace, "chunks": result.chunks}, ensure_ascii=False, sort_keys=True
    )
    secret_leaked = bool(secret and secret in serialized)
    return {
        "case_id": case["case_id"],
        "category": case["category"],
        "passed": fallback_succeeded and not invalid_output_accepted and not secret_leaked,
        "legacy_compatible": None,
        "fallback_succeeded": fallback_succeeded,
        "invalid_output_accepted": invalid_output_accepted,
        "secret_leaked": secret_leaked,
        "trace": trace,
    }


def build_report(fixture_path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    fixture = load_fixture(fixture_path)
    cases = [evaluate_case(case, fixture["base"]) for case in fixture["cases"]]
    fallback_cases = [case for case in cases if case["category"] != "legacy"]
    legacy_cases = [case for case in cases if case["category"] == "legacy"]
    legacy_rate = sum(case["legacy_compatible"] for case in legacy_cases) / len(
        legacy_cases
    )
    return build_case_report(
        fixture_path=fixture_path,
        fixture=fixture,
        cases=cases,
        metrics={
            "topic11_fallback_success_rate": (
                sum(case["fallback_succeeded"] for case in fallback_cases)
                / len(fallback_cases)
            ),
            "topic11_invalid_output_acceptance_count": sum(
                case["invalid_output_accepted"] for case in cases
            ),
            "secret_leak_count": sum(case["secret_leaked"] for case in cases),
            "legacy_compatibility_rate": legacy_rate,
            "legacy_request_regression": int(legacy_rate != 1.0),
            "legacy_package_regression": int(legacy_rate != 1.0),
        },
        reproduction_command="python scripts/eval_topic5_topic11_adapter.py",
        claim_boundary=(
            "Measures deterministic offline Topic 11 adapter contracts with fixture and "
            "mock transports; it makes no live-service availability claim."
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    write_json_report(build_report(args.fixture), args.output)


if __name__ == "__main__":
    main()
