from app.schemas.target_schema import TargetField
from app.services.transform_service import TransformService


def field(field_id: str, field_type: str = "array[string]") -> TargetField:
    return TargetField(
        field_id=field_id,
        name=field_id,
        display_name=field_id,
        type=field_type,
    )


def test_list_normalizer_splits_numbered_items_and_filters_noise() -> None:
    source = (
        "申请条件：\n"
        "1. 依法登记注册；\n"
        "2、近三年无重大违法记录\n"
        "第 1 页\n"
        "责任编辑：张三"
    )

    normalized, error = TransformService()._coerce_value(
        source,
        field("application_conditions"),
        {},
    )

    assert normalized == ["依法登记注册", "近三年无重大违法记录"]
    assert error is None


def test_list_normalizer_preserves_order_and_wraps_single_item() -> None:
    service = TransformService()

    topics, error = service._coerce_value(
        "审议年度预算、研究安全生产；部署民生工作",
        field("topics"),
        {},
    )
    single, single_error = service._coerce_value(
        "面向本市中小企业",
        field("applicable_scope"),
        {},
    )

    assert topics == ["审议年度预算", "研究安全生产", "部署民生工作"]
    assert error is None
    assert single == ["面向本市中小企业"]
    assert single_error is None


def test_uncertain_list_split_is_flagged_for_review() -> None:
    flags = TransformService()._list_quality_flags(
        "符合条件的企业和事业单位",
        ["符合条件的企业和事业单位"],
    )

    assert flags == ["list_split_review_required"]


def test_organization_cleaner_removes_labels_but_keeps_joint_publishers() -> None:
    service = TransformService()

    issuer, error = service._coerce_value(
        "发布机构：工业和信息化部、国家发展改革委",
        field("issuer", "string"),
        {},
    )
    site, site_error = service._coerce_value(
        "来源：市政务服务局网站",
        field("issuing_body", "string"),
        {},
    )

    assert issuer == "工业和信息化部、国家发展改革委"
    assert error is None
    assert site == "市政务服务局"
    assert site_error is None

