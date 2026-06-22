from app.engines.transform_engine import TransformEngine
from app.schemas.mapping import FieldMapping
from app.schemas.transform import TransformRule
from app.schemas.uir import UIRDocument


def make_uir(**extra_metadata: object) -> UIRDocument:
    return UIRDocument(
        uir_version="1.0",
        doc_id="doc_test",
        metadata={"title": "test", "doc_type": "通知", **extra_metadata},
        blocks=[],
    )


def make_mapping(
    target_field_id: str,
    source_path: str,
    source_name: str = "",
    status: str = "confirmed",
) -> FieldMapping:
    return FieldMapping(
        mapping_id="map_test",
        task_id="task_test",
        candidate_id="cand_test",
        source_field={"source_path": source_path, "source_name": source_name},
        target_field_id=target_field_id,
        target_field_name=target_field_id,
        method="exact_match",
        confidence=1.0,
        status=status,
    )


def _run(uir, mappings, rules, enum_maps=None, defaults=None):
    engine = TransformEngine()
    return engine.execute(
        uir=uir,
        mappings=mappings,
        transform_rules=rules,
        enum_maps=enum_maps or {},
        defaults=defaults or {},
    )


def test_rename_moves_source_value_to_target():
    uir = make_uir()
    mappings = [make_mapping("title", "metadata.title")]
    fields, traces = _run(uir, mappings, [])
    assert fields["title"].value == "test"
    assert len(traces) == 0


def test_type_cast_integer_to_string():
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_test",
        metadata={"count": 42},
        blocks=[],
    )
    mappings = [make_mapping("count", "metadata.count")]
    rules = [
        TransformRule(
            rule_id="r1",
            operation="type_cast",
            target_field_id="count",
            params={"to": "string"},
        )
    ]
    fields, traces = _run(uir, mappings, rules)
    assert fields["count"].value == "42"
    assert fields["count"].type == "string"
    assert any(t["action"] == "type_cast" for t in traces)


def test_type_cast_string_to_integer():
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_test",
        metadata={"count": "123"},
        blocks=[],
    )
    mappings = [make_mapping("count", "metadata.count")]
    rules = [
        TransformRule(
            rule_id="r1",
            operation="type_cast",
            target_field_id="count",
            params={"to": "integer"},
        )
    ]
    fields, traces = _run(uir, mappings, rules)
    assert fields["count"].value == 123
    assert fields["count"].type == "integer"


def test_type_cast_string_to_float():
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_test",
        metadata={"price": "9.99"},
        blocks=[],
    )
    mappings = [make_mapping("price", "metadata.price")]
    rules = [
        TransformRule(
            rule_id="r1",
            operation="type_cast",
            target_field_id="price",
            params={"to": "float"},
        )
    ]
    fields, _ = _run(uir, mappings, rules)
    assert fields["price"].value == 9.99


def test_type_cast_string_to_bool():
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_test",
        metadata={"active": "true"},
        blocks=[],
    )
    mappings = [make_mapping("active", "metadata.active")]
    rules = [
        TransformRule(
            rule_id="r1",
            operation="type_cast",
            target_field_id="active",
            params={"to": "bool"},
        )
    ]
    fields, _ = _run(uir, mappings, rules)
    assert fields["active"].value is True


def test_date_format_chinese_date():
    uir = make_uir(publish_date="2026年6月1日")
    mappings = [make_mapping("publish_date", "metadata.publish_date")]
    rules = [
        TransformRule(
            rule_id="r1",
            operation="date_format",
            target_field_id="publish_date",
            params={"output_format": "YYYY-MM-DD"},
        )
    ]
    fields, traces = _run(uir, mappings, rules)
    assert fields["publish_date"].value == "2026-06-01"
    assert any(t["action"] == "date_format" for t in traces)


def test_date_format_iso_date_passthrough():
    uir = make_uir(publish_date="2026-06-01")
    mappings = [make_mapping("publish_date", "metadata.publish_date")]
    rules = [
        TransformRule(
            rule_id="r1",
            operation="date_format",
            target_field_id="publish_date",
            params={"output_format": "YYYY-MM-DD"},
        )
    ]
    fields, _ = _run(uir, mappings, rules)
    assert fields["publish_date"].value == "2026-06-01"


def test_enum_map_hits():
    uir = make_uir()
    mappings = [make_mapping("doc_type", "metadata.doc_type")]
    rules = [
        TransformRule(
            rule_id="r1",
            operation="enum_map",
            target_field_id="doc_type",
        )
    ]
    enum_maps = {"doc_type": {"通知": "notice", "制度": "policy"}}
    fields, traces = _run(uir, mappings, rules, enum_maps=enum_maps)
    assert fields["doc_type"].value == "notice"
    assert any(t["status"] == "success" for t in traces)


def test_enum_map_miss_warning():
    uir = make_uir(doc_type="其他")
    mappings = [make_mapping("doc_type", "metadata.doc_type")]
    rules = [
        TransformRule(
            rule_id="r1",
            operation="enum_map",
            target_field_id="doc_type",
        )
    ]
    enum_maps = {"doc_type": {"通知": "notice"}}
    _, traces = _run(uir, mappings, rules, enum_maps=enum_maps)
    assert any(t["status"] == "warning" for t in traces)


def test_default_fills_missing_field():
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_test",
        metadata={},
        blocks=[],
    )
    mappings: list[FieldMapping] = []
    rules = [
        TransformRule(
            rule_id="r1",
            operation="default",
            target_field_id="language",
            params={"value": "zh-CN"},
        )
    ]
    fields, traces = _run(uir, mappings, rules)
    assert fields["language"].value == "zh-CN"
    assert any(t["action"] == "default_value" for t in traces)


def test_merge_combines_multiple_sources():
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_test",
        metadata={"main_title": "数据治理", "sub_title": "管理办法"},
        blocks=[],
    )
    mappings = [
        make_mapping("main_title", "metadata.main_title"),
        make_mapping("sub_title", "metadata.sub_title"),
    ]
    rules = [
        TransformRule(
            rule_id="r1",
            operation="merge",
            target_field_id="full_title",
            source_fields=["metadata.main_title", "metadata.sub_title"],
            params={"separator": "：", "skip_empty": True},
        )
    ]
    fields, traces = _run(uir, mappings, rules)
    assert fields["full_title"].value == "数据治理：管理办法"
    assert any(t["action"] == "merge" for t in traces)


def test_split_breaks_into_fields():
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_test",
        metadata={"org_full": "信息中心|IC"},
        blocks=[],
    )
    mappings = [make_mapping("org_full", "metadata.org_full")]
    rules = [
        TransformRule(
            rule_id="r1",
            operation="split",
            source_field="metadata.org_full",
            target_fields=["org_name", "org_code"],
            params={"separator": "|"},
        )
    ]
    fields, traces = _run(uir, mappings, rules)
    assert fields["org_name"].value == "信息中心"
    assert fields["org_code"].value == "IC"
    assert any(t["action"] == "split" for t in traces)


def test_unconfirmed_mapping_skipped():
    uir = make_uir()
    mappings = [make_mapping("title", "metadata.title", status="review_required")]
    fields, _ = _run(uir, mappings, [])
    assert "title" not in fields


def test_defaults_dict_fills_missing():
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_test",
        metadata={},
        blocks=[],
    )
    defaults = {"language": "zh-CN", "doc_type": "policy"}
    fields, traces = _run(uir, [], [], defaults=defaults)
    assert fields["language"].value == "zh-CN"
    assert fields["doc_type"].value == "policy"


def test_chinese_date_with_spaces():
    uir = make_uir(publish_date="2026 年 6 月 1 日")
    mappings = [make_mapping("publish_date", "metadata.publish_date")]
    rules = [
        TransformRule(
            rule_id="r1",
            operation="date_format",
            target_field_id="publish_date",
            params={},
        )
    ]
    fields, _ = _run(uir, mappings, rules)
    assert fields["publish_date"].value == "2026-06-01"
