import json
from pathlib import Path

from app.services.external_uir_adapter_service import ExternalUIRAdapterService
from app.services.schema_router_service import SchemaRouterService

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "examples" / "external_uir"
ROUTER_EXPECTED = FIXTURES / "expected" / "router_expected.jsonl"


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_router_top1_accuracy_on_expanded_fixtures() -> None:
    adapter = ExternalUIRAdapterService()
    router = SchemaRouterService()
    rows = read_jsonl(ROUTER_EXPECTED)
    correct = 0

    for expected in rows:
        payload = json.loads(
            (FIXTURES / expected["fixture"]).read_text(encoding="utf-8")
        )
        uir, report = adapter.adapt_from_dict(payload, source_system="quality-polish")
        decision = router.route(uir, adapter_report=report)
        if (
            decision.selected_schema_id == expected["expected_schema_id"]
            and decision.selected_template_id == expected["expected_template_id"]
        ):
            correct += 1
        assert decision.confidence >= expected["min_confidence"]
        if not expected["allow_review_required"]:
            assert decision.review_required is False

    assert correct / len(rows) >= 0.85
