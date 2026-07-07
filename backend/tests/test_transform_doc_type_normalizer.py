import pytest

from app.schemas.target_schema import TargetField
from app.services.transform_service import TransformService


def doc_type_field() -> TargetField:
    return TargetField(
        field_id="doc_type",
        name="doc_type",
        display_name="文档类型",
        type="enum",
        constraints={"enum": ["policy", "notice", "measure"]},
    )


@pytest.mark.parametrize(
    "source_value",
    ["政策", "政策文件", "政策通知", "通知", "办法", "规则", "指南", "policy", "policy_doc"],
)
def test_policy_doc_type_normalizer_maps_known_values(source_value: str) -> None:
    normalized, issue = TransformService()._coerce_value(source_value, doc_type_field(), {})

    assert normalized == "policy"
    assert issue is None


def test_policy_doc_type_normalizer_does_not_map_meeting_to_policy() -> None:
    normalized, issue = TransformService()._coerce_value("会议纪要", doc_type_field(), {})

    assert normalized == "会议纪要"
    assert issue is not None
    assert issue["code"] == "enum_normalization_warning"
    assert issue["field_id"] == "doc_type"


def test_policy_doc_type_normalizer_keeps_unknown_value_with_warning() -> None:
    normalized, issue = TransformService()._coerce_value("unknown_type", doc_type_field(), {})

    assert normalized == "unknown_type"
    assert issue is not None
    assert issue["code"] == "enum_normalization_warning"
