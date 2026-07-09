from typing import Any

from app.schemas.external_uir import (
    AdapterReport,
    RouteEvidence,
    SchemaRouteCandidate,
    SchemaRouteDecision,
)
from app.schemas.uir import UIRDocument
from app.services.schema_pack_service import SchemaPackService


class SchemaRouterService:
    THRESHOLD_AUTO = 0.75
    THRESHOLD_REVIEW = 0.50
    ROUTE_VERSION = "2.0"

    SIGNALS: dict[str, dict[str, Any]] = {
        "procurement_doc": {
            "template_id": "procurement_doc_base_v1",
            "keywords": [
                "采购",
                "招标",
                "中标",
                "成交",
                "供应商",
                "采购人",
                "代理机构",
                "预算金额",
                "中标金额",
                "项目编号",
            ],
            "field_labels": ["供应商", "采购人", "代理机构", "预算金额", "中标金额", "项目编号"],
            "risks": {
                "预算金额": "budget_amount_not_award_amount",
                "控制价": "control_price_not_award_amount",
            },
        },
        "policy_doc": {
            "template_id": "policy_doc_base_v1",
            "keywords": [
                "政策",
                "通知",
                "办法",
                "意见",
                "指南",
                "实施方案",
                "发布机构",
                "发布机关",
                "发文机关",
                "成文日期",
                "发布日期",
                "有效期",
            ],
            "field_labels": ["发布机构", "发布机关", "发文机关", "成文日期", "发布日期", "有效期"],
            "risks": {
                "成文日期": "written_date_not_publish_date",
                "retrieved_at": "retrieved_at_not_effective_date",
            },
        },
        "meeting_doc": {
            "template_id": "meeting_doc_base_v1",
            "keywords": [
                "会议",
                "纪要",
                "主持人",
                "参会",
                "参会人员",
                "议题",
                "研究事项",
                "审议",
                "会议时间",
                "会议编号",
            ],
            "field_labels": ["主持人", "参会", "参会人员", "议题", "会议时间", "会议编号"],
            "risks": {
                "主持人": "host_not_attendee",
                "联系人": "contact_not_attendee",
            },
        },
        "contract_doc": {
            "template_id": "contract_doc_base_v1",
            "keywords": [
                "合同",
                "协议",
                "甲方",
                "乙方",
                "金额",
                "期限",
                "生效",
                "履约",
                "签订",
                "签订日期",
                "有效期",
            ],
            "field_labels": ["甲方", "乙方", "金额", "期限", "签订日期", "有效期"],
            "risks": {},
        },
        "general_doc": {
            "template_id": "general_doc_base_v1",
            "keywords": [
                "服务指南",
                "办事指南",
                "申报",
                "申报指南",
                "申请条件",
                "办理流程",
                "材料清单",
                "所需材料",
                "服务对象",
                "联系方式",
            ],
            "field_labels": [
                "申请条件",
                "办理流程",
                "材料清单",
                "所需材料",
                "服务对象",
                "联系方式",
            ],
            "risks": {},
        },
    }

    def __init__(self, schema_pack_service: SchemaPackService | None = None) -> None:
        self.schema_pack_service = schema_pack_service or SchemaPackService()

    def route(
        self,
        uir: UIRDocument,
        *,
        adapter_report: AdapterReport | None = None,
    ) -> SchemaRouteDecision:
        candidates = sorted(
            (
                self._score_family(
                    schema_id=schema_id,
                    template_id=str(config["template_id"]),
                    keywords=list(config["keywords"]),
                    field_labels=list(config["field_labels"]),
                    risks=dict(config["risks"]),
                    source=str(config.get("source") or "builtin_signals"),
                    scoring=dict(config.get("scoring", {})),
                    uir=uir,
                    adapter_report=adapter_report,
                )
                for schema_id, config in self._signals().items()
            ),
            key=lambda item: item.confidence,
            reverse=True,
        )
        best = candidates[0]
        if best.confidence >= self.THRESHOLD_REVIEW:
            selected_schema_id = best.schema_id
            selected_template_id = best.template_id
        else:
            selected_schema_id = None
            selected_template_id = None

        review_required = best.confidence < self.THRESHOLD_AUTO
        decision_reason = (
            f"selected {best.schema_id} from {len(best.evidence)} evidence items"
            if selected_schema_id
            else "no existing schema family reached routing threshold"
        )
        alternatives = [
            {
                "schema_id": candidate.schema_id,
                "template_id": candidate.template_id,
                "confidence": candidate.confidence,
                "matched_keywords": [
                    item.value
                    for item in candidate.evidence
                    if item.evidence_type == "keyword"
                ],
                "reasons": candidate.reasons,
                "risk_flags": candidate.risk_flags,
                "source": candidate.source,
            }
            for candidate in candidates
        ]
        return SchemaRouteDecision(
            selected_schema_id=selected_schema_id,
            selected_template_id=selected_template_id,
            confidence=best.confidence,
            reason=decision_reason,
            alternatives=alternatives,
            review_required=review_required,
            candidates=candidates,
            decision_reason=decision_reason,
            route_version=self.ROUTE_VERSION,
        )

    def _score_family(
        self,
        *,
        schema_id: str,
        template_id: str,
        keywords: list[str],
        field_labels: list[str],
        risks: dict[str, str],
        source: str,
        scoring: dict[str, Any],
        uir: UIRDocument,
        adapter_report: AdapterReport | None,
    ) -> SchemaRouteCandidate:
        metadata_text = self._metadata_text(uir)
        block_sources = self._block_sources(uir)
        document_text = "\n".join([metadata_text, *(text for _, text in block_sources)])
        table_sources = self._table_sources(uir)

        metadata_matches = self._matches(keywords, metadata_text)
        keyword_matches = self._matches(
            keywords,
            "\n".join(text for _, text in block_sources),
        )
        field_matches = self._matches(field_labels, document_text)
        table_matches = self._matches(
            field_labels,
            "\n".join(text for _, text in table_sources),
        )
        adapter_hint = bool(adapter_report and schema_id in adapter_report.route_hints)

        component_scores = {
            "metadata": min(1.0, len(metadata_matches) / 2),
            "keyword": min(1.0, len(keyword_matches) / 5),
            "field_hint": min(1.0, len(field_matches) / 3),
            "table_label": min(1.0, len(table_matches) / 3),
            "adapter_hint": 1.0 if adapter_hint else 0.0,
        }
        component_weights = {
            "metadata": 0.30,
            "keyword": 0.25,
            "field_hint": 0.25,
            "table_label": 0.10,
            "adapter_hint": 0.10,
        }
        component_weights.update(
            {
                key: float(value)
                for key, value in scoring.items()
                if key in component_weights and isinstance(value, int | float)
            }
        )
        confidence = round(
            sum(
                component_scores[name] * component_weights[name]
                for name in component_scores
            ),
            4,
        )

        evidence = self._evidence(
            schema_id=schema_id,
            metadata_matches=metadata_matches,
            block_sources=block_sources,
            keyword_matches=keyword_matches,
            field_matches=field_matches,
            table_sources=table_sources,
            table_matches=table_matches,
            adapter_hint=adapter_hint,
        )
        reasons = [
            f"{name} score {component_scores[name]:.2f} x {component_weights[name]:.2f}"
            for name in component_scores
            if component_scores[name] > 0
        ]
        risk_flags = [flag for token, flag in risks.items() if token in document_text]
        return SchemaRouteCandidate(
            schema_id=schema_id,
            template_id=template_id,
            confidence=confidence,
            reasons=reasons,
            evidence=evidence,
            risk_flags=risk_flags,
            source=source,
        )

    def _signals(self) -> dict[str, dict[str, Any]]:
        loaded = self.schema_pack_service.load_router_rules()
        if not loaded:
            return self.SIGNALS
        merged = dict(self.SIGNALS)
        merged.update(loaded)
        return merged

    def _evidence(
        self,
        *,
        schema_id: str,
        metadata_matches: list[str],
        block_sources: list[tuple[str, str]],
        keyword_matches: list[str],
        field_matches: list[str],
        table_sources: list[tuple[str, str]],
        table_matches: list[str],
        adapter_hint: bool,
    ) -> list[RouteEvidence]:
        evidence = [
            RouteEvidence(
                evidence_type="metadata",
                value=value,
                source_path="metadata",
                weight=0.30,
                matched_schema=schema_id,
            )
            for value in metadata_matches
        ]
        evidence.extend(
            self._source_evidence(
                evidence_type="keyword",
                values=keyword_matches,
                sources=block_sources,
                weight=0.25,
                schema_id=schema_id,
            )
        )
        evidence.extend(
            self._source_evidence(
                evidence_type="field_hint",
                values=field_matches,
                sources=[("metadata", self._join_sources(block_sources))],
                weight=0.25,
                schema_id=schema_id,
            )
        )
        evidence.extend(
            self._source_evidence(
                evidence_type="table_label",
                values=table_matches,
                sources=table_sources,
                weight=0.10,
                schema_id=schema_id,
            )
        )
        if adapter_hint:
            evidence.append(
                RouteEvidence(
                    evidence_type="adapter_hint",
                    value=schema_id,
                    source_path="adapter_report.route_hints",
                    weight=0.10,
                    matched_schema=schema_id,
                )
            )
        return evidence

    @staticmethod
    def _source_evidence(
        *,
        evidence_type: str,
        values: list[str],
        sources: list[tuple[str, str]],
        weight: float,
        schema_id: str,
    ) -> list[RouteEvidence]:
        items: list[RouteEvidence] = []
        for value in values:
            source_path = next(
                (path for path, text in sources if value in text),
                None,
            )
            items.append(
                RouteEvidence(
                    evidence_type=evidence_type,
                    value=value,
                    source_path=source_path,
                    weight=weight,
                    matched_schema=schema_id,
                )
            )
        return items

    @staticmethod
    def _matches(tokens: list[str], text: str) -> list[str]:
        return [token for token in tokens if token in text]

    @staticmethod
    def _metadata_text(uir: UIRDocument) -> str:
        return "\n".join(str(value) for value in uir.metadata.values())

    @staticmethod
    def _block_sources(uir: UIRDocument) -> list[tuple[str, str]]:
        return [
            (f"blocks[{index}].text", block.text)
            for index, block in enumerate(uir.blocks)
            if block.text
        ]

    @staticmethod
    def _table_sources(uir: UIRDocument) -> list[tuple[str, str]]:
        sources: list[tuple[str, str]] = []
        for index, block in enumerate(uir.blocks):
            rows = block.attributes.get("rows")
            if isinstance(rows, list):
                sources.append((f"blocks[{index}].attributes.rows", str(rows)))
        return sources

    @staticmethod
    def _join_sources(sources: list[tuple[str, str]]) -> str:
        return "\n".join(text for _, text in sources)
