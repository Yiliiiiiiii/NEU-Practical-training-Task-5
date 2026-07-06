import json
from pathlib import Path

from app.services.candidate_service import CandidateService
from app.services.external_uir_adapter_service import ExternalUIRAdapterService
from app.services.mapping_service import MappingService
from app.services.schema_service import SchemaService
from app.services.template_service import TemplateService

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "examples" / "external_uir"
PRODUCTION_LIKE = ROOT / "examples" / "production_like"
BADCASES = FIXTURES / "expected" / "badcases.jsonl"


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_external_uir_badcases_are_never_auto_accepted() -> None:
    adapter = ExternalUIRAdapterService()
    schema_service = SchemaService(PRODUCTION_LIKE / "schemas")
    template_service = TemplateService(PRODUCTION_LIKE / "mapping_templates")

    for badcase in read_jsonl(BADCASES):
        payload = json.loads(
            (FIXTURES / badcase["fixture"]).read_text(encoding="utf-8")
        )
        uir, _report = adapter.adapt_from_dict(
            payload,
            source_system="quality-polish",
        )
        schema_id = badcase["schema_id"]
        template_id = badcase["template_id"]
        candidates = CandidateService().extract_candidates(
            f"task_{uir.doc_id}",
            uir,
        )
        mapping = MappingService().map_fields(
            f"task_{uir.doc_id}",
            uir,
            schema_service.load_schema(schema_id),
            template_service.load_template(template_id),
            candidates,
            options={
                "badcases": [
                    {
                        "source_field": badcase["source_label"],
                        "forbidden_target_fields": [badcase["forbidden_target"]],
                    }
                ]
            },
        )

        assert not any(
            item["source_field_name"] == badcase["source_label"]
            and item["target_field_id"] == badcase["forbidden_target"]
            and item["status"] == "accepted"
            for item in mapping.mappings
        )
