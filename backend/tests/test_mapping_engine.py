from app.clients.llm_client import LLMClient
from app.engines.mapping_engine import MappingEngine
from app.schemas.mapping import FieldCandidate
from app.schemas.mapping_template import MappingTemplate, RegexRule
from app.schemas.target_schema import TargetField, TargetSchema


def make_candidate(
    source_name: str,
    value_sample: str,
    inferred_type: str = "string",
) -> FieldCandidate:
    return FieldCandidate(
        candidate_id=f"cand_{source_name}",
        task_id="task_test",
        doc_id="doc_test",
        source_path=f"metadata.{source_name}",
        source_name=source_name,
        display_name=source_name,
        value_sample=value_sample,
        inferred_type=inferred_type,
        confidence=0.95,
    )


def make_schema(field: TargetField) -> TargetSchema:
    return TargetSchema(
        schema_id="schema_test",
        name="test schema",
        version="1.0.0",
        fields=[field],
    )


def make_template(
    aliases: dict[str, list[str]] | None = None,
    regex_rules: list[RegexRule] | None = None,
) -> MappingTemplate:
    return MappingTemplate(
        template_id="template_test",
        schema_id="schema_test",
        name="test template",
        version="1.0.0",
        aliases=aliases or {},
        regex_rules=regex_rules or [],
    )


def map_one(
    candidate: FieldCandidate,
    target: TargetField,
    template: MappingTemplate | None = None,
):
    mappings = MappingEngine().map_fields(
        task_id="task_test",
        candidates=[candidate],
        target_schema=make_schema(target),
        template=template or make_template(),
        review_threshold=0.8,
    )
    assert len(mappings) == 1
    return mappings[0]


def test_exact_match_has_full_confidence():
    target = TargetField(
        field_id="title",
        name="title",
        display_name="Title",
        type="string",
    )

    mapping = map_one(make_candidate("title", "SchemaPack"), target)

    assert mapping.method == "exact_match"
    assert mapping.confidence == 1.0


def test_alias_match_supports_chinese_aliases():
    target = TargetField(
        field_id="title",
        name="title",
        display_name="标题",
        type="string",
        aliases=["文档标题"],
    )

    mapping = map_one(make_candidate("文档标题", "数据平台手册"), target)

    assert mapping.method == "alias_match"
    assert mapping.confidence == 0.95


def test_regex_match_applies_template_pattern_to_candidate_value():
    target = TargetField(
        field_id="published_date",
        name="published_date",
        display_name="发布日期",
        type="date",
    )
    template = make_template(
        regex_rules=[
            RegexRule(
                target_field_id="published_date",
                pattern=r"发布日期[:：]\s*(\d{4}年\d{1,2}月\d{1,2}日)",
                group=1,
            )
        ]
    )
    candidate = make_candidate(
        "body_text",
        "发布日期：2026年6月22日",
        inferred_type="string",
    )

    mapping = map_one(candidate, target, template)

    assert mapping.method == "regex_match"
    assert mapping.confidence == 0.9
    assert "2026年6月22日" in mapping.evidence


def test_type_match_maps_a_compatible_date_candidate():
    target = TargetField(
        field_id="effective_date",
        name="effective_date",
        display_name="生效日期",
        type="date",
    )

    mapping = map_one(
        make_candidate("document_time", "2026-06-22", inferred_type="date"),
        target,
    )

    assert mapping.method == "type_match"
    assert mapping.confidence == 0.8


def test_fuzzy_match_maps_similar_names():
    target = TargetField(
        field_id="document_title",
        name="document title",
        display_name="Document title",
        type="string",
    )

    mapping = map_one(make_candidate("document titl", "SchemaPack"), target)

    assert mapping.method == "fuzzy_match"
    assert 0.6 < mapping.confidence < 0.8


def test_llm_client_returns_structured_mock_suggestion_only_when_enabled():
    candidates = [{"candidate_id": "cand_title"}]
    target_fields = [{"field_id": "title"}]

    assert LLMClient(enabled=False).suggest_mappings(candidates, target_fields) == []

    suggestions = LLMClient(enabled=True).suggest_mappings(candidates, target_fields)

    assert [suggestion.model_dump() for suggestion in suggestions] == [
        {
            "candidate_id": "cand_title",
            "target_field_id": "title",
            "confidence": 0.5,
            "reason": "mock suggestion",
        }
    ]
