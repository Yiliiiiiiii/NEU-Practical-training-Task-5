from collections import Counter
from typing import Any

from app.schemas.uir import UIRBlock, UIRDocument
from app.schemas.uir_quality_gate import (
    UIRQualityGateIssue,
    UIRQualityGatePolicy,
    UIRQualityGateReport,
    UIRQualityGateStatus,
)
from app.services.schema_router_service import SchemaRouterService


class UIRQualityGateService:
    SUPPORTED_SCHEMA_IDS = {
        "general_doc",
        "meeting_doc",
        "policy_doc",
        "procurement_doc",
    }
    TEMPLATE_IDS = {
        "general_doc": "general_doc_base_v1",
        "meeting_doc": "meeting_doc_base_v1",
        "policy_doc": "policy_doc_base_v1",
        "procurement_doc": "procurement_doc_base_v1",
    }
    MOJIBAKE_MARKERS = (
        "�",
        "锛",
        "鐢",
        "鏃",
        "鍙",
        "绫",
        "鈥",
        "",
        "",
        "鏈",
        "鍔",
        "鏉",
        "鑱",
        "娓",
        "呭",
    )

    def __init__(self, router: SchemaRouterService | None = None) -> None:
        self._router = router or SchemaRouterService()

    def evaluate(self, uir: UIRDocument) -> UIRQualityGateReport:
        issues = self._structural_issues(uir)
        route = self._router.route(uir)
        metadata_schema_id = self._metadata_schema_id(uir)
        supported_doc_type = (
            route.selected_schema_id
            if route.selected_schema_id in self.SUPPORTED_SCHEMA_IDS
            else None
        )
        selected_schema_id = route.selected_schema_id
        selected_template_id = route.selected_template_id

        if supported_doc_type is None and metadata_schema_id:
            supported_doc_type = metadata_schema_id
            selected_schema_id = metadata_schema_id
            selected_template_id = self.TEMPLATE_IDS[metadata_schema_id]
            issues.append(
                self._issue(
                    "metadata_schema_fallback",
                    "warning",
                    "review",
                    "Schema route fell below threshold; metadata doc_type was used "
                    "as a review-only fallback.",
                )
            )

        if selected_schema_id is None:
            issues.append(
                self._issue(
                    "unsupported_schema_family",
                    "error",
                    "unsupported",
                    "No supported schema family reached the routing threshold.",
                )
            )
        elif supported_doc_type is None:
            issues.append(
                self._issue(
                    "unsupported_schema_family",
                    "error",
                    "unsupported",
                    "Schema family "
                    f"{selected_schema_id!r} is not enabled for Phase D mapping.",
                )
            )
        elif route.review_required:
            issues.append(
                self._issue(
                    "low_route_confidence",
                    "warning",
                    "review",
                    "Schema routing selected a supported family but did not reach auto confidence.",
                )
            )

        status = self._status(issues)
        quality_score = self._quality_score(issues, route.confidence)
        return UIRQualityGateReport(
            doc_id=uir.doc_id,
            status=status,
            quality_score=quality_score,
            supported_doc_type=supported_doc_type,
            selected_schema_id=selected_schema_id,
            selected_template_id=selected_template_id,
            schema_route_confidence=route.confidence,
            mapping_policy=self._mapping_policy(status),
            issues=issues,
        )

    def _structural_issues(self, uir: UIRDocument) -> list[UIRQualityGateIssue]:
        issues: list[UIRQualityGateIssue] = []
        if not uir.blocks:
            issues.append(
                self._issue(
                    "missing_blocks",
                    "error",
                    "reject",
                    "UIR contains no blocks to map.",
                    "blocks",
                )
            )
            return issues

        block_ids = [block.block_id for block in uir.blocks]
        duplicate_ids = sorted(
            block_id for block_id, count in Counter(block_ids).items() if count > 1
        )
        if duplicate_ids:
            issues.append(
                self._issue(
                    "duplicate_block_id",
                    "error",
                    "reject",
                    f"Duplicate block ids: {', '.join(duplicate_ids[:5])}.",
                    "blocks",
                )
            )

        text_values = [self._block_text(block) for block in uir.blocks]
        meaningful_texts = [text for text in text_values if len(text.strip()) >= 2]
        if not meaningful_texts:
            issues.append(
                self._issue(
                    "missing_text_evidence",
                    "error",
                    "reject",
                    "UIR blocks contain no meaningful text evidence.",
                    "blocks",
                )
            )
        elif len(meaningful_texts) / len(uir.blocks) < 0.3:
            issues.append(
                self._issue(
                    "low_text_coverage",
                    "warning",
                    "review",
                    "Less than 30% of UIR blocks contain meaningful text.",
                    "blocks",
                )
            )

        document_text = "\n".join(
            [self._metadata_text(uir.metadata), *meaningful_texts]
        )
        if self._mojibake_ratio(document_text) > 0.015:
            issues.append(
                self._issue(
                    "possible_mojibake",
                    "warning",
                    "review",
                    "UIR text appears to contain mojibake or replacement characters.",
                )
            )

        if not self._has_title_evidence(uir):
            issues.append(
                self._issue(
                    "missing_title_evidence",
                    "warning",
                    "review",
                    "No title-like metadata or heading block was found.",
                )
            )

        if not self._has_source_evidence(uir):
            issues.append(
                self._issue(
                    "missing_source_evidence",
                    "warning",
                    "review",
                    "No source_url, source_site, or source_sha256 evidence was found.",
                )
            )

        return issues

    def _mapping_policy(self, status: UIRQualityGateStatus) -> UIRQualityGatePolicy:
        if status == "pass":
            return UIRQualityGatePolicy(
                allow_auto_accept=True,
                require_review_for_high_risk_fields=True,
                allow_llm_suggestions=True,
            )
        if status == "review":
            return UIRQualityGatePolicy(
                allow_auto_accept=False,
                require_review_for_high_risk_fields=True,
                allow_llm_suggestions=True,
            )
        return UIRQualityGatePolicy(
            allow_auto_accept=False,
            require_review_for_high_risk_fields=True,
            allow_llm_suggestions=False,
        )

    def _status(self, issues: list[UIRQualityGateIssue]) -> UIRQualityGateStatus:
        actions = {issue.action for issue in issues}
        if "reject" in actions:
            return "reject"
        if "unsupported" in actions:
            return "unsupported"
        if "review" in actions:
            return "review"
        return "pass"

    def _quality_score(
        self,
        issues: list[UIRQualityGateIssue],
        route_confidence: float,
    ) -> float:
        penalty = 0.0
        for issue in issues:
            if issue.action in {"reject", "unsupported"}:
                penalty += 0.35
            elif issue.severity == "warning":
                penalty += 0.08
            else:
                penalty += 0.03
        return round(max(0.0, min(1.0, route_confidence - penalty)), 4)

    def _has_source_evidence(self, uir: UIRDocument) -> bool:
        metadata = uir.metadata
        return bool(
            metadata.get("source_url")
            or metadata.get("source_site")
            or metadata.get("source_sha256")
        )

    def _metadata_schema_id(self, uir: UIRDocument) -> str | None:
        for key in ("doc_type", "domain", "schema_id"):
            value = uir.metadata.get(key)
            if isinstance(value, str) and value in self.SUPPORTED_SCHEMA_IDS:
                return value
        return None

    def _has_title_evidence(self, uir: UIRDocument) -> bool:
        if uir.metadata.get("title") or uir.metadata.get("标题") or uir.metadata.get("鏍囬"):
            return True
        return any(
            block.type in {"title", "heading"} or block.level == 1
            for block in uir.blocks
        )

    def _block_text(self, block: UIRBlock) -> str:
        parts: list[str] = []
        if block.text:
            parts.append(block.text)
        parts.extend(self._flatten_values(block.attributes))
        return " ".join(part for part in parts if part)

    def _metadata_text(self, metadata: dict[str, Any]) -> str:
        return " ".join(self._flatten_values(metadata))

    def _flatten_values(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, int | float | bool):
            return [str(value)]
        if isinstance(value, dict):
            result: list[str] = []
            for key, item in value.items():
                result.append(str(key))
                result.extend(self._flatten_values(item))
            return result
        if isinstance(value, list | tuple):
            result = []
            for item in value:
                result.extend(self._flatten_values(item))
            return result
        return [str(value)]

    def _mojibake_ratio(self, text: str) -> float:
        if not text:
            return 0.0
        marker_hits = sum(text.count(marker) for marker in self.MOJIBAKE_MARKERS)
        return marker_hits / len(text)

    def _issue(
        self,
        code: str,
        severity: str,
        action: UIRQualityGateStatus,
        message: str,
        path: str | None = None,
    ) -> UIRQualityGateIssue:
        return UIRQualityGateIssue(
            code=code,
            severity=severity,
            action=action,
            message=message,
            path=path,
        )
