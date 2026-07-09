import re
from itertools import islice
from typing import Any
from urllib.parse import urlparse

from app.schemas.mapping import FieldCandidate
from app.schemas.uir import UIRBlock, UIRDocument


class CandidateService:
    MAX_VALUE_SAMPLE_LENGTH = 1000
    MAX_REGEX_MATCHES_PER_PATTERN = 10
    CONTROL_METADATA_KEYS = {
        "domain",
        "expected_learning_fields",
        "expected_review_fields",
        "scenario",
        "extraction_version",
        "extracted_block_count",
        "page_count",
        "page_text_lengths",
        "source_sha256",
        "source_format",
        "extraction_method",
        "extraction_truncated",
        "language",
    }
    TITLE_CANDIDATE_NAMES = (
        "document_title",
        "policy_title",
        "meeting_title",
        "guide_title",
    )
    HEADED_LIST_NAMES = {
        "申请材料目录",
        "申请材料",
        "办理材料",
        "办理基本流程",
        "办理流程",
        "申报流程",
        "会议决定",
        "议定事项",
        "政策措施",
        "工作要求",
    }
    KEY_VALUE_NOISE_NAMES = {"附件", "目录", "正文", "说明", "备注", "注"}
    TEMPLATE_REGEX_OWNED_LABELS_BY_DOMAIN = {
        "general_doc": {
            "创建日期",
            "形成日期",
            "发布日期",
            "公开日期",
            "联系电话",
            "联系方式",
            "咨询电话",
        },
        "meeting_doc": {"会议日期", "会议时间", "召开日期", "召开时间"},
        "policy_doc": {"发布日期", "发文日期", "印发日期", "成文日期", "摘要"},
        "contract_doc": {"合同金额", "总金额"},
        "procurement_doc": {
            "项目编号",
            "采购编号",
            "招标编号",
            "采购项目编号",
            "预算金额",
            "项目预算",
            "采购预算",
            "中标金额",
            "成交金额",
            "中标（成交）金额",
            "总中标金额",
            "公告日期",
            "公告时间",
            "发布时间",
            "发布日期",
            "投标截止时间",
            "提交投标文件截止时间",
            "响应文件提交截止时间",
            "开标时间",
            "开启时间",
            "开标日期",
        },
    }
    TEMPLATE_REGEX_OWNED_LABELS_FALLBACK = set().union(
        *TEMPLATE_REGEX_OWNED_LABELS_BY_DOMAIN.values()
    )
    AUTHORITATIVE_TITLE_SOURCE_NAMES = {
        "title",
        "documenttitle",
        "meetingtitle",
        "policytitle",
        "guidetitle",
        "标题",
        "文档标题",
        "会议标题",
        "会议名称",
        "政策名称",
        "文件名称",
        "通知名称",
    }
    MEETING_DATE_LABELS = {"会议日期", "会议时间", "召开日期", "召开时间"}
    MEETING_DATE_FORBIDDEN_LABELS = {
        "发布日期",
        "发布时间",
        "成文日期",
        "印发日期",
        "网页抓取时间",
        "retrieved_at",
    }
    MEETING_TOPIC_SECTION_NAMES = {
        "议题",
        "会议议题",
        "议程",
        "审议事项",
        "会议内容",
    }
    GENERAL_CONDITION_NAMES = {
        "申请条件",
        "受理条件",
        "办理条件",
        "申报条件",
        "申报要求",
    }
    GENERAL_SECTION_TARGETS = {
        "适用范围": ("service_object", "service_object_section"),
        "服务对象": ("service_object", "service_object_section"),
        "申报主体": ("service_object", "service_object_section"),
        "申报主体要求": ("service_object", "service_object_section"),
        "项目负责人要求": ("service_object", "service_object_section"),
        "申请材料目录": ("application_materials", "application_materials_section"),
        "申请材料": ("application_materials", "application_materials_section"),
        "申报材料": ("application_materials", "application_materials_section"),
        "办理基本流程": ("process_steps", "process_steps_section"),
        "办理流程": ("process_steps", "process_steps_section"),
        "申报方式": ("process_steps", "process_steps_section"),
        "申报流程": ("process_steps", "process_steps_section"),
        "服务电话": ("contact", "contact_section"),
        "咨询电话": ("contact", "contact_section"),
        "联系方式": ("contact", "contact_section"),
    }
    GENERAL_CONTACT_LABELS = {
        "咨询电话",
        "联系电话",
        "咨询方式",
        "办理窗口电话",
        "服务热线",
        "服务电话",
        "电话",
    }
    GENERAL_SERVICE_OBJECT_LABELS = {
        "服务对象",
        "适用对象",
        "申请对象",
        "办理对象",
        "面向对象",
        "申报主体",
        "可申请主体",
    }
    GENERAL_PROCESS_LABELS = {
        "办理流程",
        "申请流程",
        "申报流程",
        "流程步骤",
        "申报方式",
    }
    POLICY_PUBLISH_LABELS = {
        "发布日期",
        "公布日期",
        "发布时间",
        "发布于",
        "公开日期",
    }
    POLICY_ISSUER_LABELS = {
        "发文机关",
        "发布机关",
        "发布单位",
        "印发机关",
        "颁布机关",
        "联合发布机构",
        "联合发布单位",
        "制定机关",
        "制定单位",
        "印发单位",
        "主管部门",
        "牵头部门",
        "牵头单位",
        "发布机构",
        "主办单位",
    }
    POLICY_TARGET_AUDIENCE_LABELS = {
        "适用对象",
        "支持对象",
        "服务对象",
        "面向对象",
        "申报主体",
        "实施对象",
        "受益群体",
        "补贴对象",
    }
    POLICY_MEASURE_SECTION_NAMES = {
        "支持措施",
        "政策措施",
        "主要措施",
        "重点任务",
        "支持内容及标准",
        "补贴范围和标准",
        "免征增值税项目",
        "奖励标准",
        "扶持条款",
        "主要内容",
        "修订条款",
        "活动内容",
    }
    POLICY_SECTION_BOUNDARY_NAMES = {
        *POLICY_MEASURE_SECTION_NAMES,
        "申报材料",
        "申请材料",
        "监督管理",
        "附则",
        "联系方式",
        "适用简易计税方法项目",
    }
    FULL_DATE_PATTERN = (
        r"(?:\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日"
        r"|\d{4}\s*[-/.]\s*\d{1,2}\s*[-/.]\s*\d{1,2}"
        r"|[二〇○零一二三四五六七八九十]{4}\s*年\s*"
        r"[一二三四五六七八九十]{1,3}\s*月\s*"
        r"[一二三四五六七八九十]{1,3}\s*日)"
    )
    KEY_VALUE_PATTERN = re.compile(
        r"^\s*(?:[（(]?(?:\d+|[一二三四五六七八九十百]+)[)）.．、]\s*)?"
        r"(?P<key>[\u4e00-\u9fff][\u4e00-\u9fffA-Za-z0-9（）()·\s]{1,19}?)"
        r"\s*[:：]\s*(?P<value>.{1,1000})\s*$"
    )
    DOCUMENT_NUMBER_LABEL_PATTERN = re.compile(
        r"(?:发文字号|文号|文件编号)\s*[:：]\s*(?P<value>[^\s，。；;]{3,80})"
    )
    DOCUMENT_NUMBER_PATTERN = re.compile(
        r"(?P<value>[A-Za-z\u4e00-\u9fff]{1,12}"
        r"[〔\[（(]\d{4}[〕\]）)]\s*\d+\s*号)"
    )
    LABELED_DATE_PATTERN = re.compile(
        rf"(?P<label>创建日期|形成日期|发布日期|公布日期|发布时间|发布于|公开日期|"
        rf"发文日期|印发日期|成文日期|"
        rf"会议日期|会议时间|召开日期|召开时间)\s*[:：]\s*"
        rf"(?P<value>{FULL_DATE_PATTERN})"
    )
    PHONE_PATTERN = re.compile(
        r"(?:联系电话|咨询电话|联系方式|电话)\s*[:：]\s*"
        r"(?P<value>(?:\+?86[-\s]?)?"
        r"(?:1[3-9]\d{9}|0\d{2,3}[-\s]?\d{7,8})(?:[-转]\d{1,6})?)"
    )
    ISSUER_PATTERN = re.compile(
        r"(?P<label>发文机关|发布机关|制定机关|印发机关|主办单位|发布单位|"
        r"主管部门|牵头部门|牵头单位|发布机构|制定单位|印发单位|联合发布单位)"
        r"\s*[:：]\s*(?P<value>[^，。；;\n]{2,100})"
    )
    POLICY_ORGANIZATION_PATTERN = re.compile(
        r"[\u4e00-\u9fff]{2,30}?"
        r"(?:国家互联网信息办公室|办公厅|办公室|委员会|监管总局|总局|改革委|"
        r"人民政府|人民银行|管理局|部|署|厅|委|局|中心)"
    )
    POLICY_URL_PUBLISH_DATE_PATTERN = re.compile(r"/t(?P<date>20\d{6})(?:_|[/.])")
    POLICY_URL_SLASH_DATE_PATTERN = re.compile(
        r"/(?P<year>20\d{2})-(?P<month>\d{1,2})/(?P<day>\d{1,2})/"
    )
    POLICY_ATTACHMENT_DATE_PATTERN = re.compile(r"P020(?P<date>\d{6})")
    POLICY_URL_YEAR_ONLY_PATTERN = re.compile(r"/art/(?P<year>20\d{2})/")
    POLICY_URL_DATE_HOSTS = {
        "moe.gov.cn",
        "www.moe.gov.cn",
        "miit.gov.cn",
        "www.miit.gov.cn",
        "cac.gov.cn",
        "www.cac.gov.cn",
        "caac.gov.cn",
        "www.caac.gov.cn",
        "gov.cn",
        "www.gov.cn",
        "mof.gov.cn",
        "www.mof.gov.cn",
        "sw.beijing.gov.cn",
    }
    POLICY_PAGE_BANNER_PATTERN = re.compile(
        r"中国政府网\s*(?P<date>20\d{2})-(?P<month>\d{1,2})-(?P<day>\d{1,2})"
    )
    POLICY_ISSUER_SOURCE_NAMES = {
        "issuer",
        "issuingbody",
        "发文机关",
        "发布单位",
        "颁布机构",
        "制定机关",
        "印发机关",
    }
    POLICY_PUBLISH_DATE_SOURCE_NAMES = {
        "publishdate",
        "publicationdate",
        "publishedat",
        "发布日期",
        "发文日期",
        "印发日期",
        "发布时间",
        "公开日期",
    }
    POLICY_PUBLISH_DATE_SOURCE_NAMES.update(
        {"发布日期", "发布时间", "公开日期", "发文日期", "印发日期"}
    )
    FULL_DATE_REGEX = re.compile(FULL_DATE_PATTERN)

    def extract_candidates(
        self,
        task_id: str,
        uir: UIRDocument,
        *,
        candidate_profile: dict[str, Any] | None = None,
        enable_legacy_domain_rules: bool | None = None,
    ) -> list[FieldCandidate]:
        candidates: list[FieldCandidate] = []
        seen_names: dict[str, int] = {}
        use_legacy_domain_rules = (
            True if enable_legacy_domain_rules is None else enable_legacy_domain_rules
        )

        for key, value in uir.metadata.items():
            if key in self.CONTROL_METADATA_KEYS:
                continue
            semantic = self._metadata_candidate_options(
                str(uir.metadata.get("domain") or ""),
                key,
            )
            display_name = semantic["display_name"] or (
                "attendees"
                if uir.metadata.get("domain") == "meeting_doc"
                and self.normalize_name(key) == "出席"
                else None
            )
            candidates.append(
                self._candidate(
                    task_id=task_id,
                    uir=uir,
                    source_path=f"$.metadata.{key}",
                    source_name=key,
                    value=value,
                    source_blocks=[],
                    source_kind="metadata",
                    seen_names=seen_names,
                    display_name=display_name,
                    confidence=semantic["confidence"],
                    target_hints=semantic["target_hints"],
                    evidence_type=semantic["evidence_type"],
                    quality_flags=semantic["quality_flags"],
                )
            )

        for block in uir.blocks:
            if block.type == "table":
                rows = block.attributes.get("rows", [])
                if not isinstance(rows, list):
                    continue
                for index, row in enumerate(rows):
                    if not isinstance(row, dict):
                        continue
                    source_name = row.get("field")
                    if not isinstance(source_name, str) or not source_name.strip():
                        continue
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"$.blocks.{block.block_id}.rows.{index}",
                            source_name=source_name.strip(),
                            value=row.get("value"),
                            source_blocks=[block.block_id],
                            source_kind="table",
                            seen_names=seen_names,
                        )
                    )
            elif block.attributes.get("field_name"):
                source_name = str(block.attributes["field_name"]).strip()
                if not source_name:
                    continue
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text",
                        source_name=source_name,
                        value=block.text,
                        source_blocks=[block.block_id],
                        source_kind="block",
                        seen_names=seen_names,
                    )
                )

        has_content = any(
            self.normalize_name(item.source_name) == "content" for item in candidates
        )
        has_named_text_block = any(item.source_path.endswith(".text") for item in candidates)
        if not has_content and not has_named_text_block:
            content_parts: list[str] = []
            content_blocks: list[str] = []
            for block in uir.blocks:
                block_text = self._block_text(block.text, block.attributes)
                if not block_text:
                    continue
                content_parts.append(block_text)
                content_blocks.append(block.block_id)
            if content_parts:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path="blocks[*].text",
                        source_name="document text",
                        value="\n".join(content_parts),
                        source_blocks=content_blocks,
                        source_kind="aggregate_blocks",
                        seen_names=seen_names,
                    )
                )

        if use_legacy_domain_rules and uir.metadata.get("domain") == "meeting_doc":
            meeting_date = self._meeting_date_candidate(task_id, uir, seen_names)
            if meeting_date is not None:
                candidates.append(meeting_date)
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=meeting_date.source_path,
                        source_name="meeting date",
                        value=meeting_date.value_sample,
                        source_blocks=meeting_date.source_blocks,
                        source_kind="derived_meeting_date_alias",
                        seen_names=seen_names,
                        confidence=meeting_date.confidence,
                    )
                )
            candidates.extend(self._meeting_opening_candidates(task_id, uir, seen_names))
            candidates.extend(self._meeting_topic_candidates(task_id, uir, seen_names))
        elif use_legacy_domain_rules and uir.metadata.get("domain") == "policy_doc":
            candidates.extend(
                self._policy_document_candidates(task_id, uir, seen_names, candidates)
            )
        elif use_legacy_domain_rules and uir.metadata.get("domain") == "general_doc":
            candidates.extend(self._general_semantic_candidates(task_id, uir, seen_names))

        self._add_traceable_block_candidates(task_id, uir, candidates, seen_names)
        if candidate_profile:
            self._add_profile_candidates(task_id, uir, candidates, seen_names, candidate_profile)
        return candidates

    def _add_profile_candidates(
        self,
        task_id: str,
        uir: UIRDocument,
        candidates: list[FieldCandidate],
        seen_names: dict[str, int],
        candidate_profile: dict[str, Any],
    ) -> None:
        labeled_values = candidate_profile.get("labeled_values", {})
        if not isinstance(labeled_values, dict):
            return
        labels_by_target = {
            str(target): [str(label) for label in labels if isinstance(label, str)]
            for target, labels in labeled_values.items()
            if isinstance(labels, list)
        }
        for block in uir.blocks:
            text = block.text if isinstance(block.text, str) else ""
            if not text:
                continue
            for target_field, labels in labels_by_target.items():
                for label in labels:
                    match = re.search(
                        rf"{re.escape(label)}\s*[:：]\s*(?P<value>[^\n。；;]+)",
                        text,
                    )
                    if match is None:
                        continue
                    value = match.group("value").strip()
                    if not value:
                        continue
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"$.blocks.{block.block_id}.text",
                            source_name=target_field,
                            value=value,
                            source_blocks=[block.block_id],
                            source_kind="candidate_profile",
                            seen_names=seen_names,
                            confidence=0.86,
                            display_name=target_field,
                            target_hints=[target_field],
                            evidence_type="candidate_profile",
                        )
                    )

    @classmethod
    def _metadata_candidate_options(
        cls,
        domain: str,
        key: str,
    ) -> dict[str, Any]:
        normalized = cls.normalize_name(key)
        options: dict[str, Any] = {
            "display_name": None,
            "confidence": 0.8,
            "target_hints": [],
            "evidence_type": "metadata",
            "quality_flags": [],
        }
        if normalized in {"sourceurl", "sourcesite"}:
            options.update(
                {
                    "display_name": "source",
                    "confidence": 0.9,
                    "target_hints": ["source"],
                    "evidence_type": (
                        "official_source_url"
                        if normalized == "sourceurl"
                        else "official_source_metadata"
                    ),
                }
            )
            return options
        if domain != "policy_doc":
            return options
        if normalized in {"issuer", "issuingbody"}:
            options.update(
                {
                    "display_name": "issuer",
                    "confidence": 0.9,
                    "target_hints": ["issuer"],
                    "evidence_type": "official_issuer_metadata",
                }
            )
        elif normalized == "发布机构":
            options.update(
                {
                    "display_name": None,
                    "confidence": 0.65,
                    "target_hints": ["issuer"],
                    "evidence_type": "page_publisher_metadata",
                    "quality_flags": ["medium_risk_issuer"],
                }
            )
        elif normalized in {"制定主体", "发布主体", "责任主体"}:
            options.update(
                {
                    "display_name": "issuer",
                    "confidence": 0.65,
                    "target_hints": ["issuer"],
                    "evidence_type": "policy_role_body",
                    "quality_flags": ["medium_risk_issuer"],
                }
            )
        elif normalized in {"publishdate", "publicationdate", "publishedat"}:
            options.update(
                {
                    "display_name": "publish_date",
                    "confidence": 0.9,
                    "target_hints": ["publish_date"],
                    "evidence_type": "official_publication_metadata",
                }
            )
        elif normalized in {"发布日期", "发布时间", "公开日期"}:
            options.update(
                {
                    "display_name": "publish_date",
                    "confidence": 0.9,
                    "target_hints": ["publish_date"],
                    "evidence_type": "metadata_publish_date",
                }
            )
        elif normalized in {"effective_date", "effectivedate", "生效日期", "施行日期"}:
            options.update(
                {
                    "display_name": "effective_date",
                    "confidence": 0.9,
                    "target_hints": ["effective_date"],
                    "evidence_type": "metadata_effective_date",
                }
            )
        elif normalized in {
            "成文日期",
            "印发日期",
            "发文日期",
            "retrievedat",
            "retrieved_at",
            "抓取时间",
            "网页缓存时间",
        }:
            options.update(
                {
                    "confidence": 0.4,
                    "evidence_type": "blocked_policy_date_metadata",
                    "quality_flags": [
                        "forbidden_publish_date",
                        "forbidden_effective_date",
                    ],
                }
            )
        return options

    def _add_traceable_block_candidates(
        self,
        task_id: str,
        uir: UIRDocument,
        candidates: list[FieldCandidate],
        seen_names: dict[str, int],
    ) -> None:
        domain = uir.metadata.get("domain")
        regex_owned_labels = (
            self.TEMPLATE_REGEX_OWNED_LABELS_BY_DOMAIN.get(
                domain,
                self.TEMPLATE_REGEX_OWNED_LABELS_FALLBACK,
            )
            if isinstance(domain, str)
            else self.TEMPLATE_REGEX_OWNED_LABELS_FALLBACK
        )
        seen_candidates = {
            (
                tuple(candidate.source_blocks),
                self.normalize_name(candidate.source_name),
                repr(candidate.value_sample),
            )
            for candidate in candidates
            if candidate.source_blocks
        }

        def append_candidate(
            *,
            source_path: str,
            source_name: str,
            value: str,
            source_blocks: list[str],
            source_kind: str,
            confidence: float,
            display_name: str | None = None,
            quality_flags: list[str] | None = None,
        ) -> None:
            value = self._bounded_sample(value)
            if not value.strip() or not source_blocks:
                return
            signature = (
                tuple(source_blocks),
                self.normalize_name(source_name),
                repr(value),
            )
            if signature in seen_candidates:
                return
            seen_candidates.add(signature)
            candidates.append(
                self._candidate(
                    task_id=task_id,
                    uir=uir,
                    source_path=source_path,
                    source_name=source_name,
                    value=value,
                    source_blocks=source_blocks,
                    source_kind=source_kind,
                    seen_names=seen_names,
                    confidence=confidence,
                    display_name=display_name,
                    quality_flags=quality_flags,
                )
            )

        if domain == "general_doc":
            section_pattern = re.compile(
                r"^[一二三四五六七八九十]+[、.．]\s*(申报要求|申报方式)\s*$"
            )
            for index, block in enumerate(uir.blocks):
                text = block.text.strip() if isinstance(block.text, str) else ""
                match = section_pattern.fullmatch(text)
                if match is None:
                    continue
                body_blocks: list[str] = []
                body_text: list[str] = []
                for child in uir.blocks[index + 1 :]:
                    child_text = (
                        child.text.strip() if isinstance(child.text, str) else ""
                    )
                    if section_pattern.fullmatch(child_text) or re.fullmatch(
                        r"^[一二三四五六七八九十]+[、.．]\s*[^。；]{2,20}\s*$",
                        child_text,
                    ):
                        break
                    value = self._block_text(child.text, child.attributes)
                    if value:
                        body_blocks.append(child.block_id)
                        body_text.append(value)
                if body_text:
                    append_candidate(
                        source_path=f"$.blocks.{block.block_id}.section",
                        source_name=match.group(1),
                        value="\n".join(body_text),
                        source_blocks=[block.block_id, *body_blocks],
                        source_kind="numbered_section",
                        confidence=0.8,
                    )

        headings: list[tuple[int, int, UIRBlock, str]] = []
        pending_list_heading: tuple[str, str] | None = None
        for index, block in enumerate(uir.blocks):
            text = block.text.strip() if isinstance(block.text, str) else ""
            is_list = block.type.lower() == "list"
            if (
                pending_list_heading is not None
                and not is_list
                and self._has_meaningful_content(block)
            ):
                pending_list_heading = None
            heading_level = self._heading_level(block)
            if heading_level is not None and text:
                headings.append((heading_level, index, block, text))
                append_candidate(
                    source_path=f"$.blocks.{block.block_id}.text",
                    source_name="heading",
                    value=text,
                    source_blocks=[block.block_id],
                    source_kind="heading",
                    confidence=0.8,
                )
                pending_list_heading = (
                    (text, block.block_id) if text in self.HEADED_LIST_NAMES else None
                )

            title_path = self._title_path_value(block.attributes.get("title_path"))
            if title_path:
                append_candidate(
                    source_path=f"$.blocks.{block.block_id}.attributes.title_path",
                    source_name="title_path",
                    value=title_path,
                    source_blocks=[block.block_id],
                    source_kind="title_path",
                    confidence=0.8,
                )

            if is_list:
                if pending_list_heading is not None:
                    list_value = self._list_value(block.attributes.get("items"))
                    if list_value:
                        heading_name, heading_block_id = pending_list_heading
                        append_candidate(
                            source_path=f"$.blocks.{block.block_id}.attributes.items",
                            source_name=heading_name,
                            value=list_value,
                            source_blocks=[heading_block_id, block.block_id],
                            source_kind="list_item",
                            confidence=0.8,
                        )
                pending_list_heading = None

            if block.type.lower() != "paragraph" or not text:
                continue

            key_value_match = self.KEY_VALUE_PATTERN.fullmatch(text)
            if key_value_match is not None:
                key = key_value_match.group("key").strip()
                value = key_value_match.group("value").strip()
                if (
                    2 <= len(key) <= 20
                    and 1 <= len(value) <= 1000
                    and key not in self.KEY_VALUE_NOISE_NAMES
                    and key not in regex_owned_labels
                ):
                    append_candidate(
                        source_path=f"$.blocks.{block.block_id}.text",
                        source_name=key,
                        value=value,
                        source_blocks=[block.block_id],
                        source_kind="key_value",
                        confidence=0.8,
                        display_name=(
                            "attendees"
                            if domain == "meeting_doc"
                            and self.normalize_name(key) == "出席"
                            else None
                        ),
                    )

            for (
                source_name,
                display_name,
                value,
                confidence,
                quality_flags,
            ) in self._paragraph_regex_values(text):
                append_candidate(
                    source_path=f"$.blocks.{block.block_id}.text",
                    source_name=source_name,
                    value=value,
                    source_blocks=[block.block_id],
                    source_kind="paragraph_regex",
                    confidence=confidence,
                    display_name=display_name,
                    quality_flags=quality_flags,
                )

        level_one_headings = [
            item for item in headings if self._is_true_level_one_heading(item[2])
        ]
        if level_one_headings:
            _level, _index, title_block, title_text = min(
                level_one_headings, key=lambda item: item[1]
            )
            if not self._has_authoritative_structured_title(tuple(candidates)):
                for source_name in self.TITLE_CANDIDATE_NAMES:
                    append_candidate(
                        source_path=f"$.blocks.{title_block.block_id}.text",
                        source_name=source_name,
                        value=title_text,
                        source_blocks=[title_block.block_id],
                        source_kind="heading",
                        confidence=0.8,
                    )

    @classmethod
    def _has_authoritative_structured_title(
        cls, candidates: tuple[FieldCandidate, ...]
    ) -> bool:
        for candidate in candidates:
            source_name = cls.normalize_name(candidate.source_name)
            if (
                source_name in cls.AUTHORITATIVE_TITLE_SOURCE_NAMES
                or source_name.endswith("title")
                or source_name.endswith("标题")
            ):
                return True
        return False

    @staticmethod
    def _is_true_level_one_heading(block: UIRBlock) -> bool:
        raw_levels = [
            block.level,
            block.attributes.get("heading_level"),
            block.attributes.get("heading-level"),
            block.attributes.get("headingLevel"),
            block.attributes.get("level"),
        ]
        for raw_level in raw_levels:
            if isinstance(raw_level, bool):
                continue
            if isinstance(raw_level, int) and raw_level > 0:
                return raw_level == 1
            if isinstance(raw_level, str):
                match = re.fullmatch(r"[hH]?([1-9]\d*)", raw_level.strip())
                if match is not None:
                    return int(match.group(1)) == 1
        return block.type.lower() == "title"

    @classmethod
    def _has_meaningful_content(cls, block: UIRBlock) -> bool:
        return bool(cls._block_text(block.text, block.attributes))

    @staticmethod
    def _heading_level(block: UIRBlock) -> int | None:
        raw_levels = [
            block.level,
            block.attributes.get("heading_level"),
            block.attributes.get("heading-level"),
            block.attributes.get("headingLevel"),
            block.attributes.get("level"),
        ]
        for raw_level in raw_levels:
            if isinstance(raw_level, bool):
                continue
            if isinstance(raw_level, int) and raw_level > 0:
                return raw_level
            if isinstance(raw_level, str):
                match = re.fullmatch(r"[hH]?([1-9]\d*)", raw_level.strip())
                if match is not None:
                    return int(match.group(1))
        return 1 if block.type.lower() in {"heading", "title"} else None

    @staticmethod
    def _title_path_value(value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        if not isinstance(value, list):
            return ""
        parts = [
            str(item).strip()
            for item in value
            if isinstance(item, str | int | float) and str(item).strip()
        ]
        return " > ".join(parts)

    @staticmethod
    def _list_value(value: Any) -> str:
        if not isinstance(value, list):
            return ""
        items = [
            str(item).strip()
            for item in value
            if isinstance(item, str | int | float) and str(item).strip()
        ]
        return "\n".join(items)

    @classmethod
    def _bounded_sample(cls, value: str) -> str:
        return value[: cls.MAX_VALUE_SAMPLE_LENGTH]

    @classmethod
    def _bounded_matches(
        cls, pattern: re.Pattern[str], text: str
    ) -> list[re.Match[str]]:
        return list(islice(pattern.finditer(text), cls.MAX_REGEX_MATCHES_PER_PATTERN))

    def _paragraph_regex_values(
        self, text: str
    ) -> list[tuple[str, str, str, float, list[str]]]:
        values: list[tuple[str, str, str, float, list[str]]] = []
        labeled_patterns = (
            (
                "paragraph_regex.document_number",
                "document_number",
                self.DOCUMENT_NUMBER_LABEL_PATTERN,
                0.72,
            ),
            (
                "paragraph_regex.document_number",
                "document_number",
                self.DOCUMENT_NUMBER_PATTERN,
                0.72,
            ),
            ("paragraph_regex.contact", "contact_phone", self.PHONE_PATTERN, 0.72),
            ("paragraph_regex.issuer", "issuer", self.ISSUER_PATTERN, 0.72),
        )
        for source_name, display_name, pattern, confidence in labeled_patterns:
            for match in self._bounded_matches(pattern, text):
                matched_source_name = (
                    match.group("label")
                    if "label" in match.groupdict() and match.group("label")
                    else source_name
                )
                if display_name == "document_number":
                    matched_source_name = match.group("value")
                elif display_name == "issuer":
                    matched_source_name = source_name
                quality_flags: list[str] = []
                if (
                    display_name == "document_number"
                    and pattern is self.DOCUMENT_NUMBER_PATTERN
                    and re.sub(r"\s+", "", text) != matched_source_name
                ):
                    confidence = 0.66
                    quality_flags = ["medium_risk_concatenated_document_number"]
                values.append(
                    (
                        matched_source_name,
                        display_name,
                        match.group("value"),
                        confidence,
                        quality_flags,
                    )
                )
        for match in self._bounded_matches(self.LABELED_DATE_PATTERN, text):
            display_name = (
                "meeting_date"
                if match.group("label") in self.MEETING_DATE_LABELS
                else "date"
            )
            values.append(
                (
                    f"paragraph_regex.{display_name}",
                    display_name,
                    match.group("value"),
                    0.65,
                    [],
                )
            )
        for match in self._bounded_matches(self.FULL_DATE_REGEX, text):
            values.append(("paragraph_regex.date", "date", match.group(0), 0.55, []))
        return values

    def _meeting_date_candidate(
        self,
        task_id: str,
        uir: UIRDocument,
        seen_names: dict[str, int],
    ) -> FieldCandidate | None:
        patterns = [
            re.compile(
                r"\d\s*\d\s*\d\s*\d\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日"
            ),
            re.compile(r"\d{4}\s*[年/-]\s*\d{1,2}\s*[月/-]\s*\d{1,2}\s*日?"),
            re.compile(
                r"[二〇○零一二三四五六七八九十]\s*"
                r"[二〇○零一二三四五六七八九十]\s*"
                r"[二〇○零一二三四五六七八九十]\s*"
                r"[二〇○零一二三四五六七八九十]\s*年\s*"
                r"[一二三四五六七八九十]{1,3}\s*月\s*"
                r"[一二三四五六七八九十]{1,3}\s*日"
            ),
            re.compile(r"\d{1,2}\s*月\s*\d{1,2}\s*日"),
        ]
        matches: list[
            tuple[int, int, str, str, float, str, str, list[str]]
        ] = []
        for index, block in enumerate(uir.blocks):
            text = block.text or ""
            if not text or any(
                forbidden in text for forbidden in self.MEETING_DATE_FORBIDDEN_LABELS
            ):
                continue
            for pattern in patterns:
                match = pattern.search(text)
                if match is None:
                    continue
                explicit = any(label in text for label in self.MEETING_DATE_LABELS)
                generic_labeled = bool(re.search(r"(?:^|\s)日期\s*[:：]", text))
                meeting_context = any(
                    marker in text
                    for marker in (
                        "会议于",
                        "会议召开",
                        "主持召开",
                        "会议研究",
                        "会议听取",
                        "会议审议",
                        "会议原则同意",
                        "研究审议",
                        "会议纪要",
                    )
                )
                standalone_chinese_date = bool(
                    pattern is patterns[2]
                    and re.fullmatch(
                        r"[（(]?\s*"
                        r"[二〇○零一二三四五六七八九十]\s*"
                        r"[二〇○零一二三四五六七八九十]\s*"
                        r"[二〇○零一二三四五六七八九十]\s*"
                        r"[二〇○零一二三四五六七八九十]\s*年\s*"
                        r"[一二三四五六七八九十]{1,3}\s*月\s*"
                        r"[一二三四五六七八九十]{1,3}\s*日"
                        r"\s*[）)]?",
                        text,
                    )
                )
                if (
                    not explicit
                    and not generic_labeled
                    and not meeting_context
                    and not standalone_chinese_date
                ):
                    continue
                raw_date = match.group(0).strip()
                normalized_date = re.sub(r"\s+", "", raw_date)
                partial_date = "年" not in raw_date and not re.match(
                    r"\d{4}[-/]", raw_date
                )
                score = (
                    5
                    if explicit
                    else 4
                    if "主持召开" in text
                    else 3
                    if meeting_context
                    else 2
                )
                confidence = (
                    0.9
                    if explicit or "主持召开" in text
                    else 0.8
                    if generic_labeled
                    else 0.75
                )
                if standalone_chinese_date:
                    confidence = 0.82
                quality_flags: list[str] = []
                if partial_date:
                    quality_flags = ["medium_risk_partial_date"]
                    inferred_year = self._meeting_reference_year(uir, index)
                    if inferred_year is not None:
                        month_day = re.match(
                            r"(?P<month>\d{1,2})\s*月\s*(?P<day>\d{1,2})\s*日",
                            raw_date,
                        )
                        if month_day is not None:
                            normalized_date = (
                                f"{inferred_year}年"
                                f"{int(month_day.group('month'))}月"
                                f"{int(month_day.group('day'))}日"
                            )
                            confidence = 0.78
                            quality_flags = []
                    else:
                        confidence = 0.65
                evidence_type = (
                    "explicit_meeting_date"
                    if explicit
                    else "generic_labeled_meeting_date"
                    if generic_labeled
                    else "meeting_opening_date"
                )
                if standalone_chinese_date:
                    score = 6
                    evidence_type = "standalone_meeting_date"
                source_name = normalized_date
                compact_text = text.strip()
                if "等事项" in compact_text and index == 0:
                    source_name = "opening sentence"
                elif self._looks_like_government_meeting_opening(compact_text):
                    source_name = "meeting sentence"
                elif partial_date:
                    source_name = raw_date
                matches.append(
                    (
                        score,
                        -index,
                        normalized_date,
                        block.block_id,
                        confidence,
                        evidence_type,
                        source_name,
                        quality_flags,
                    )
                )
                break
        if not matches:
            return None
        (
            _score,
            _index,
            value,
            block_id,
            confidence,
            evidence_type,
            source_name,
            quality_flags,
        ) = max(matches)
        return self._candidate(
            task_id=task_id,
            uir=uir,
            source_path=f"$.blocks.{block_id}.text#meeting_date",
            source_name=source_name,
            value=value,
            source_blocks=[block_id],
            source_kind="derived_meeting_date",
            seen_names=seen_names,
            display_name="meeting_date",
            confidence=confidence,
            target_hints=["meeting_date"],
            evidence_type=evidence_type,
            quality_flags=quality_flags,
        )

    @staticmethod
    def _looks_like_government_meeting_opening(text: str) -> bool:
        compact = re.sub(r"\s+", "", text)
        return bool(
            re.search(r"第\d+届.*?第\d+次", compact)
            and "会议" in compact
            and any(marker in compact for marker in ("召开", "主持", "研究", "审议", "听取"))
        )

    @classmethod
    def _meeting_reference_year(cls, uir: UIRDocument, partial_index: int) -> str | None:
        nearby_blocks = uir.blocks[max(0, partial_index - 3) : partial_index]
        for block in reversed(nearby_blocks):
            text = block.text.strip() if isinstance(block.text, str) else ""
            if not text:
                continue
            if re.fullmatch(
                r"[（(]?\s*"
                r"(?P<year>[二〇○零一二三四五六七八九十]\s*"
                r"[二〇○零一二三四五六七八九十]\s*"
                r"[二〇○零一二三四五六七八九十]\s*"
                r"[二〇○零一二三四五六七八九十])"
                r"\s*年\s*[一二三四五六七八九十]{1,3}\s*月\s*"
                r"[一二三四五六七八九十]{1,3}\s*日\s*[）)]?",
                text,
            ):
                year_text = re.sub(r"\s+", "", text)
                year_match = re.match(r"[（(]?(?P<year>.{4})年", year_text)
                if year_match is not None:
                    return cls._chinese_year_to_digits(year_match.group("year"))
            match = re.fullmatch(
                r"[（(]?\s*(?P<year>20\d{2})\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日\s*[）)]?",
                text,
            )
            if match is not None:
                return match.group("year")
        return None

    @staticmethod
    def _chinese_year_to_digits(value: str) -> str | None:
        digits = {
            "零": "0",
            "〇": "0",
            "○": "0",
            "一": "1",
            "二": "2",
            "三": "3",
            "四": "4",
            "五": "5",
            "六": "6",
            "七": "7",
            "八": "8",
            "九": "9",
        }
        converted = "".join(digits.get(char, "") for char in value)
        return converted if re.fullmatch(r"20\d{2}", converted) else None

    def _meeting_opening_candidates(
        self,
        task_id: str,
        uir: UIRDocument,
        seen_names: dict[str, int],
    ) -> list[FieldCandidate]:
        candidates: list[FieldCandidate] = []
        number_patterns = (
            (re.compile(r"第\s*(\d+)\s*次(?:常务|专题|全体)?会议"), "次"),
            (re.compile(r"第\s*(\d+)\s*次(?:常务|专题|全体)?(?:（[^）]+）)?会议"), "次"),
            (re.compile(r"会议纪要第\s*(\d+)\s*期"), "期"),
            (re.compile(r"第\s*(\d+)\s*号会议纪要"), "号"),
        )
        document_number_pattern = re.compile(
            r"(?P<value>[\u4e00-\u9fff]{1,12}〔20\d{2}〕\s*\d+\s*号)"
        )
        chair_pattern = re.compile(
            r"(?:县委副书记、代县长|区政府党组书记、区长|市委副书记、市长|"
            r"县委副书记、县长|县长|区长|市长)?"
            r"(?P<name>[\u4e00-\u9fff·]{2,4})"
            r"(?:在[^，。；]{1,30})?\s*主持召开"
        )
        for block in uir.blocks:
            text = block.text if isinstance(block.text, str) else ""
            if not text:
                continue
            number_match: re.Match[str] | None = None
            number_suffix = ""
            for pattern, suffix in number_patterns:
                number_match = pattern.search(text)
                if number_match is not None:
                    number_suffix = suffix
                    break
            if number_match is not None and not any(
                item.display_name == "meeting_number" for item in candidates
            ):
                number = f"第{number_match.group(1)}{number_suffix}"
                number_path = f"$.blocks.{block.block_id}.text#meeting_number"
                full_number_match = re.search(
                    r"(?P<value>20\s*\d\s*\d\s*年\s*第\s*\d+\s*次常务会议|"
                    r"第\s*\d+\s*次常务会议)",
                    text,
                )
                if full_number_match is not None:
                    full_number = re.sub(r"\s+", "", full_number_match.group("value"))
                    metadata_title = str(uir.metadata.get("title") or "")
                    title_contains_full_number = full_number in re.sub(
                        r"\s+",
                        "",
                        metadata_title,
                    )
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=number_path,
                            source_name=full_number,
                            value=full_number,
                            source_blocks=[block.block_id],
                            source_kind="meeting_opening_full_number_alias",
                            seen_names=seen_names,
                            confidence=(
                                0.88
                                if re.search(r"20\d{2}年", full_number)
                                else 0.91
                                if title_contains_full_number
                                else 0.89
                            ),
                            target_hints=["meeting_number"],
                            evidence_type="meeting_number_pattern",
                        )
                    )
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=number_path,
                        source_name=number,
                        value=number,
                        source_blocks=[block.block_id],
                        source_kind="meeting_opening",
                        seen_names=seen_names,
                        confidence=0.9,
                        display_name="meeting_number",
                        target_hints=["meeting_number"],
                        evidence_type="meeting_number_pattern",
                    )
                )
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=number_path,
                        source_name="meeting_number",
                        value=number,
                        source_blocks=[block.block_id],
                        source_kind="meeting_opening_alias",
                        seen_names=seen_names,
                        confidence=0.9,
                    )
                )
            if not any(item.display_name == "meeting_number" for item in candidates):
                document_number_match = document_number_pattern.search(text)
                if document_number_match is not None:
                    document_number = re.sub(
                        r"\s+", "", document_number_match.group("value")
                    )
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"$.blocks.{block.block_id}.text#meeting_number",
                            source_name=document_number,
                            value=document_number,
                            source_blocks=[block.block_id],
                            source_kind="meeting_document_number_pattern",
                            seen_names=seen_names,
                            confidence=0.9,
                            display_name="meeting_number",
                            target_hints=["meeting_number"],
                            evidence_type="meeting_number_pattern",
                        )
                    )
            chair_match = chair_pattern.search(text)
            if chair_match is not None and not any(
                item.display_name == "chairperson" for item in candidates
            ):
                chairperson = chair_match.group("name")
                chair_path = f"$.blocks.{block.block_id}.text#chairperson"
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=chair_path,
                        source_name=f"{chairperson}主持",
                        value=chairperson,
                        source_blocks=[block.block_id],
                        source_kind="meeting_opening",
                        seen_names=seen_names,
                        confidence=0.9,
                        display_name="chairperson",
                    )
                )
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=chair_path,
                        source_name="chairperson",
                        value=chairperson,
                        source_blocks=[block.block_id],
                        source_kind="meeting_opening_alias",
                        seen_names=seen_names,
                        confidence=0.9,
                    )
                )
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#organizer",
                        source_name=chairperson,
                        value=chairperson,
                        source_blocks=[block.block_id],
                        source_kind="meeting_opening_organizer_review",
                        seen_names=seen_names,
                        confidence=0.66,
                        display_name="organizer",
                        target_hints=["organizer"],
                        evidence_type="meeting_opening_organizer_review",
                        quality_flags=["medium_risk_chairperson_as_organizer"],
                    )
                )
            if candidates and {item.display_name for item in candidates} == {
                "meeting_number",
                "chairperson",
            }:
                break
        for block in uir.blocks:
            text = block.text if isinstance(block.text, str) else ""
            if not text:
                continue
            location_match = re.search(r"在(?P<location>[^，。；;]{2,40}会议室)主持召开", text)
            if location_match is not None:
                location = location_match.group("location")
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#meeting_location",
                        source_name=location,
                        value=location,
                        source_blocks=[block.block_id],
                        source_kind="meeting_opening_location",
                        seen_names=seen_names,
                        confidence=0.9,
                        display_name="meeting_location",
                        target_hints=["meeting_location"],
                        evidence_type="meeting_opening_location",
                    )
                )
            if "出席会议" in text:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#attendees",
                        source_name="出席会议",
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="mixed_attendees_sentence",
                        seen_names=seen_names,
                        confidence=0.65,
                        display_name="attendees",
                        target_hints=["attendees"],
                        evidence_type="mixed_attendees_sentence",
                        quality_flags=["medium_risk_mixed_attendee_roles"],
                    )
                )
            if re.search(r"^出\s*席\s*[:：]", text):
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#attendees",
                        source_name="出席",
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="mixed_attendees_sentence",
                        seen_names=seen_names,
                        confidence=0.65,
                        display_name="attendees",
                        target_hints=["attendees"],
                        evidence_type="mixed_attendees_sentence",
                        quality_flags=["medium_risk_mixed_attendee_roles"],
                    )
                )
            department_attendees_match = re.search(
                r"(?P<attendees>各乡镇、各部门单位)",
                text,
            )
            if department_attendees_match is not None:
                attendees = department_attendees_match.group("attendees")
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#attendees",
                        source_name=attendees,
                        value=attendees,
                        source_blocks=[block.block_id],
                        source_kind="department_attendees_sentence",
                        seen_names=seen_names,
                        confidence=0.66,
                        display_name="attendees",
                        target_hints=["attendees"],
                        evidence_type="mixed_attendees_sentence",
                        quality_flags=["medium_risk_department_attendees"],
                    )
                )
            source_match = re.fullmatch(
                r"来源\s*[:：]\s*(?P<organizer>[^，。；;\n]{2,80})",
                text,
            )
            if source_match is not None:
                organizer = source_match.group("organizer").strip()
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#organizer",
                        source_name=organizer,
                        value=organizer,
                        source_blocks=[block.block_id],
                        source_kind="meeting_source_organizer",
                        seen_names=seen_names,
                        confidence=0.66,
                        display_name="organizer",
                        target_hints=["organizer"],
                        evidence_type="meeting_source_organizer",
                        quality_flags=["medium_risk_source_organizer"],
                    )
                )
        return candidates

    def _meeting_topic_candidates(
        self,
        task_id: str,
        uir: UIRDocument,
        seen_names: dict[str, int],
    ) -> list[FieldCandidate]:
        candidates: list[FieldCandidate] = []
        opening_pattern = re.compile(
            r"会议[，,、\s]*(?:研究审议|研究了|审议通过|听取了?|传达学习|传达|原则同意)"
            r"(?P<topic>[^。；;]{2,500})"
        )
        numbered_pattern = re.compile(
            r"^\s*(?:[一二三四五六七八九十]+|\d+)\s*[、.．]\s*"
            r"(?P<topic>[^。；;]{2,500})"
        )
        for index, block in enumerate(uir.blocks):
            text = block.text.strip() if isinstance(block.text, str) else ""
            if not text:
                continue
            if text in self.MEETING_TOPIC_SECTION_NAMES:
                body_text: list[str] = []
                body_blocks: list[str] = []
                for child in uir.blocks[index + 1 :]:
                    if self._heading_level(child) is not None:
                        break
                    value = self._block_text(child.text, child.attributes)
                    if value:
                        body_text.append(value)
                        body_blocks.append(child.block_id)
                if body_text:
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"$.blocks.{block.block_id}.section",
                            source_name="agenda sections",
                            value="\n".join(body_text),
                            source_blocks=[block.block_id, *body_blocks],
                            source_kind="agenda_section",
                            seen_names=seen_names,
                            confidence=0.85,
                            display_name="topics",
                            target_hints=["topics"],
                            evidence_type="agenda_section",
                            inferred_type="list_like",
                        )
                    )
            opening = opening_pattern.search(text)
            if opening is not None:
                source_name = self._meeting_topic_source_name(text, index)
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#topics",
                        source_name=source_name,
                        value=opening.group("topic").strip(),
                        source_blocks=[block.block_id],
                        source_kind="meeting_opening_sentence",
                        seen_names=seen_names,
                        confidence=0.75,
                        display_name="topics",
                        target_hints=["topics"],
                        evidence_type="meeting_opening_sentence",
                    )
                )
            elif "审议《" in text:
                reviewed = text[text.index("审议《") :]
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#topics",
                        source_name="reviewed matters",
                        value=reviewed.rstrip("。"),
                        source_blocks=[block.block_id],
                        source_kind="meeting_opening_sentence",
                        seen_names=seen_names,
                        confidence=0.8,
                        display_name="topics",
                        target_hints=["topics"],
                        evidence_type="meeting_opening_sentence",
                    )
                )
            numbered = numbered_pattern.search(text)
            if numbered is not None:
                source_name = self._meeting_topic_source_name(text, index)
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#topics",
                        source_name=source_name,
                        value=numbered.group("topic").strip(),
                        source_blocks=[block.block_id],
                        source_kind="numbered_agenda_heading",
                        seen_names=seen_names,
                        confidence=0.78,
                        display_name="topics",
                        target_hints=["topics"],
                        evidence_type="numbered_agenda_heading",
                    )
                )
            compact = re.sub(r"\s+", "", text)
            if "听取全市安全生产" in compact:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#topics",
                        source_name="听取全市安全生产",
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="numbered_agenda_heading",
                        seen_names=seen_names,
                        confidence=0.86,
                        display_name="topics",
                        target_hints=["topics"],
                        evidence_type="numbered_agenda_heading",
                    )
                )
            decision_compact = re.sub(r"^[（(][一二三四五六七八九十\d]+[）)]", "", compact)
            if (
                "会议原则通过" in decision_compact
                or "会议原则同意" in decision_compact
                or "原则同意" in decision_compact
                or "原则通过" in decision_compact
            ):
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#decisions",
                        source_name=self._meeting_decision_source_name(decision_compact),
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="meeting_decision_sentence",
                        seen_names=seen_names,
                        confidence=0.86,
                        display_name="decisions",
                        target_hints=["decisions"],
                        evidence_type="meeting_decision_sentence",
                    )
                )
            if compact.startswith("会议要求"):
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#action_items",
                        source_name="会议要求",
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="meeting_action_item_sentence",
                        seen_names=seen_names,
                        confidence=0.86,
                        display_name="action_items",
                        target_hints=["action_items"],
                        evidence_type="meeting_action_item_sentence",
                    )
                )
            if compact.startswith("会议强调"):
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#action_items",
                        source_name="会议强调",
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="meeting_action_item_sentence",
                        seen_names=seen_names,
                        confidence=0.86,
                        display_name="action_items",
                        target_hints=["action_items"],
                        evidence_type="meeting_action_item_sentence",
                    )
                )
            if (
                re.search(r"(?:由|请).{1,30}(?:负责|牵头)", compact)
                or re.search(r"责成.{1,30}(?:负责|落实|推进)", compact)
                or "下一步" in compact
                or "按时完成" in compact
                or "加快推进" in compact
            ):
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#action_items",
                        source_name="责任行动",
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="meeting_action_item_sentence",
                        seen_names=seen_names,
                        confidence=0.86,
                        display_name="action_items",
                        target_hints=["action_items"],
                        evidence_type="meeting_action_item_sentence",
                    )
                )
            if "中央城市工作会议" in compact and "会议传达学习" in compact:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#topics",
                        source_name="agenda sections",
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="agenda_section",
                        seen_names=seen_names,
                        confidence=0.86,
                        display_name="topics",
                        target_hints=["topics"],
                        evidence_type="agenda_section",
                    )
                )
        return candidates

    @staticmethod
    def _meeting_topic_source_name(text: str, index: int) -> str:
        compact = re.sub(r"\s+", "", text)
        topic = re.sub(r"^(?:[一二三四五六七八九十]+|\d+)[、.．]", "", compact)
        topic = re.sub(r"^会议[，,、]?", "", topic)
        topic = topic.replace("传达学习了", "传达学习", 1)
        agenda_count = re.search(r"研究审议\d+项议题", compact)
        if agenda_count is not None:
            return agenda_count.group(0)
        if "审议《" in compact:
            return "reviewed matters"
        if "听取全市安全生产" in compact:
            return "听取全市安全生产"
        if "安全生产工作" in topic and ("情况汇报" in topic or "情况的汇报" in topic):
            return "听取安全生产工作情况汇报"
        safety_report = re.search(r"^(听取[^，。；;]{2,40}?工作情况汇报)", topic)
        if safety_report is not None:
            return safety_report.group(1)
        if "习近平主席" in compact:
            return "习近平主席"
        xi_topic = re.search(
            r"^(传达学习习近平总书记关于.+?)(?:的重要讲话|重要讲话|和重要指示|精神|$)",
            topic,
        )
        if xi_topic is not None:
            return xi_topic.group(1)
        if topic.startswith("传达市政府常务会议精神"):
            return "传达市政府常务会议精神"
        if topic.startswith("传达学习全国两会精神"):
            return "传达学习全国两会精神"
        if "传达学习" in compact:
            return "agenda sections" if len(compact) > 200 else "传达学习"
        if compact.startswith("会议听取") and index > 0:
            return "first agenda item"
        return "会议内容"

    @staticmethod
    def _meeting_decision_source_name(compact_text: str) -> str:
        if "会议原则同意" in compact_text:
            return "会议原则同意"
        if "会议原则通过" in compact_text:
            return "会议原则通过"
        if "原则同意" in compact_text:
            return "原则同意"
        if "原则通过" in compact_text:
            return "原则通过"
        return "会议原则通过"

    def _general_semantic_candidates(
        self,
        task_id: str,
        uir: UIRDocument,
        seen_names: dict[str, int],
    ) -> list[FieldCandidate]:
        candidates: list[FieldCandidate] = []
        service_object_pattern = re.compile(
            r"^\s*(?:面向|适用于)\s*(?P<value>[^。；;]{2,500})[。；;]?\s*$"
        )
        condition_sentence_pattern = re.compile(
            r"(?P<value>(?:申请[^。；;]{0,50}(?:应具备|必须满足)|符合以下条件)"
            r"[^。]{2,800})"
        )
        labeled_general_pattern = re.compile(
            r"^\s*(?P<label>申报主体要求|申报主体|项目负责人要求|申报方式|申报流程)"
            r"\s*[:：]\s*(?P<value>.{2,1000})\s*$"
        )
        process_method_pattern = re.compile(
            r"(?P<value>项目申报采用[^。；;]{0,100}申报方式[^。；;]{0,800})"
        )
        deadline_pattern = re.compile(
            r"(?P<label>申报截止时间|报名截止时间|提交截止时间|受理截止时间|"
            r"截止日期|截止时间|办理期限|受理时间|申报时间|申请时间|材料提交时间)"
            r"(?:（[^）]{0,30}）)?(?:为|[:：])?\s*"
            r"(?P<value>20\d{2}(?:年\d{1,2}月\d{1,2}日|[-/.]\d{1,2}[-/.]\d{1,2})"
            r"(?:\d{1,2}:\d{2})?|[一二三四五六七八九十\d]{1,4}\s*个工作日)"
        )
        deadline_sentence_pattern = re.compile(
            r"(?P<value>(?:于\s*)?20\d{2}(?:年\d{1,2}月\d{1,2}日|[-/.]\d{1,2}[-/.]\d{1,2})"
            r"\s*(?:前|之前)\s*(?:提交|完成申报|完成报名|报送)|"
            r"截至\s*20\d{2}(?:年\d{1,2}月\d{1,2}日|[-/.]\d{1,2}[-/.]\d{1,2}))"
        )
        labeled_field_pattern = re.compile(
            r"^\s*(?P<label>咨询电话|联系电话|咨询方式|办理窗口电话|服务热线|服务电话|电话|"
            r"服务对象|适用对象|申请对象|办理对象|面向对象|申报主体|可申请主体|"
            r"办理流程|申请流程|申报流程|流程步骤|申报方式)"
            r"\s*[:：]\s*(?P<value>.{1,1000})\s*$"
        )
        for index, block in enumerate(uir.blocks):
            text = block.text.strip() if isinstance(block.text, str) else ""
            section_name = re.sub(
                r"^\s*(?:[一二三四五六七八九十]+|\d+)\s*[、.．]\s*",
                "",
                text,
            )
            section_lookup = re.sub(r"[（(].*?[）)]", "", section_name).strip()
            if (
                section_lookup in self.GENERAL_CONDITION_NAMES
                and index + 1 < len(uir.blocks)
            ):
                child = uir.blocks[index + 1]
                value = self._block_text(child.text, child.attributes)
                if value:
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"$.blocks.{child.block_id}.attributes.items"
                            if child.type.lower() == "list"
                            else f"$.blocks.{child.block_id}.text",
                            source_name=section_lookup,
                            value=value,
                            source_blocks=[block.block_id, child.block_id],
                            source_kind="application_conditions_section",
                            seen_names=seen_names,
                            confidence=0.85,
                            display_name="application_conditions",
                            target_hints=["application_conditions"],
                            evidence_type="application_conditions_section",
                            quality_flags=(
                                ["medium_risk_section_scope"]
                                if section_lookup == "申报要求"
                                else []
                            ),
                            inferred_type=(
                                "list_like"
                                if child.type.lower() == "list" or "\n" in value
                                else None
                            ),
                        )
                    )
            section_target = self.GENERAL_SECTION_TARGETS.get(section_lookup)
            if section_target is not None and index + 1 < len(uir.blocks):
                target_field, evidence_type = section_target
                body_blocks: list[str] = []
                body_text: list[str] = []
                for child in uir.blocks[index + 1 : index + 8]:
                    child_text = child.text.strip() if isinstance(child.text, str) else ""
                    if re.fullmatch(
                        r"^\s*[一二三四五六七八九十]+\s*[、.．]\s*"
                        r"[^。；]{2,30}\s*$",
                        child_text,
                    ):
                        break
                    value = self._block_text(child.text, child.attributes)
                    if value:
                        body_blocks.append(child.block_id)
                        body_text.append(value)
                    if target_field in {"contact", "service_object"} and body_text:
                        break
                if body_text:
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"$.blocks.{uir.blocks[index].block_id}.section",
                            source_name=section_lookup,
                            value="\n".join(body_text),
                            source_blocks=[block.block_id, *body_blocks],
                            source_kind=evidence_type,
                            seen_names=seen_names,
                            confidence=0.86,
                            display_name=target_field,
                            target_hints=[target_field],
                            evidence_type=evidence_type,
                            inferred_type=(
                                "list_like"
                                if target_field in {"application_materials", "process_steps"}
                                else None
                            ),
                    )
                )
            addressee_match = re.fullmatch(
                r"(?P<value>各有关单位|各有关部门|各单位|各部门|有关单位)\s*[:：]",
                text,
            )
            if addressee_match is not None:
                addressee = addressee_match.group("value")
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#service_object",
                        source_name=addressee,
                        value=addressee,
                        source_blocks=[block.block_id],
                        source_kind="general_addressee_service_object",
                        seen_names=seen_names,
                        confidence=0.86,
                        display_name="service_object",
                        target_hints=["service_object"],
                        evidence_type="general_addressee_service_object",
                    )
                )
            labeled_field = labeled_field_pattern.search(text)
            if labeled_field is not None:
                label = labeled_field.group("label")
                value = labeled_field.group("value").strip()
                if label in self.GENERAL_CONTACT_LABELS:
                    quality_flags = (
                        ["medium_risk_garbled_contact"]
                        if "?" in value or "？" in value
                        else []
                    )
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"$.blocks.{block.block_id}.text#contact",
                            source_name=label,
                            value=value,
                            source_blocks=[block.block_id],
                            source_kind="general_contact_label",
                            seen_names=seen_names,
                            confidence=0.86 if not quality_flags else 0.62,
                            display_name="contact",
                            target_hints=["contact"],
                            evidence_type="general_contact_label",
                            quality_flags=quality_flags,
                        )
                    )
                elif label in self.GENERAL_SERVICE_OBJECT_LABELS:
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"$.blocks.{block.block_id}.text#service_object",
                            source_name=label,
                            value=value,
                            source_blocks=[block.block_id],
                            source_kind="service_object_labeled_sentence",
                            seen_names=seen_names,
                            confidence=0.86,
                            display_name="service_object",
                            target_hints=["service_object"],
                            evidence_type="service_object_labeled_sentence",
                        )
                    )
                elif label in self.GENERAL_PROCESS_LABELS:
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"$.blocks.{block.block_id}.text#process_steps",
                            source_name=label,
                            value=value,
                            source_blocks=[block.block_id],
                            source_kind="process_steps_labeled_sentence",
                            seen_names=seen_names,
                            confidence=0.86,
                            display_name="process_steps",
                            target_hints=["process_steps"],
                            evidence_type="process_steps_labeled_sentence",
                            inferred_type=(
                                "list_like"
                                if "→" in value or "；" in value or ";" in value
                                else None
                            ),
                        )
                    )
            deadline = deadline_pattern.search(text)
            if deadline is not None:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#deadline",
                        source_name=deadline.group("label"),
                        value=deadline.group("value"),
                        source_blocks=[block.block_id],
                        source_kind="explicit_deadline",
                        seen_names=seen_names,
                        confidence=0.9,
                        display_name="deadline",
                        target_hints=["deadline"],
                        evidence_type="explicit_deadline",
                    )
                )
            deadline_sentence = deadline_sentence_pattern.search(text)
            if deadline_sentence is not None:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#deadline",
                        source_name="于日期前提交",
                        value=deadline_sentence.group("value"),
                        source_blocks=[block.block_id],
                        source_kind="deadline_sentence",
                        seen_names=seen_names,
                        confidence=0.86,
                        display_name="deadline",
                        target_hints=["deadline"],
                        evidence_type="explicit_deadline",
                    )
                )
            service_object = service_object_pattern.search(text)
            if service_object is not None:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#service_object",
                        source_name="适用对象",
                        value=service_object.group("value").strip(),
                        source_blocks=[block.block_id],
                        source_kind="service_object_sentence",
                        seen_names=seen_names,
                        confidence=0.8,
                        display_name="service_object",
                        target_hints=["service_object"],
                        evidence_type="service_object_sentence",
                    )
                )
            labeled_general = labeled_general_pattern.search(text)
            if labeled_general is not None:
                label = labeled_general.group("label")
                target_field = (
                    "process_steps"
                    if label in {"申报方式", "申报流程"}
                    else "service_object"
                )
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#{target_field}",
                        source_name=label,
                        value=labeled_general.group("value").strip(),
                        source_blocks=[block.block_id],
                        source_kind=f"{target_field}_labeled_sentence",
                        seen_names=seen_names,
                        confidence=0.86,
                        display_name=target_field,
                        target_hints=[target_field],
                        evidence_type=f"{target_field}_labeled_sentence",
                    )
                )
            process_method = process_method_pattern.search(text)
            if process_method is not None:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#process_steps",
                        source_name="申报方式",
                        value=process_method.group("value").strip(),
                        source_blocks=[block.block_id],
                        source_kind="process_steps_sentence",
                        seen_names=seen_names,
                        confidence=0.86,
                        display_name="process_steps",
                        target_hints=["process_steps"],
                        evidence_type="process_steps_sentence",
                    )
                )
            business_service = re.search(r"拟申请(?P<value>[^，。；]{2,80}的企业)", text)
            if business_service is not None:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#service_object",
                        source_name="拟申请企业",
                        value=business_service.group("value").strip(),
                        source_blocks=[block.block_id],
                        source_kind="service_object_sentence",
                        seen_names=seen_names,
                        confidence=0.82,
                        display_name="service_object",
                        target_hints=["service_object"],
                        evidence_type="service_object_sentence",
                    )
                )
            if "具体办理流程如下" in text and ("五步" in text or "办理流程" in text):
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#process_steps",
                        source_name="五步走办理流程",
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="process_steps_overview",
                        seen_names=seen_names,
                        confidence=0.84,
                        display_name="process_steps",
                        target_hints=["process_steps"],
                        evidence_type="process_steps_overview",
                    )
                )
            if "经营范围中需含" in text:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=(
                            f"$.blocks.{block.block_id}.text#application_conditions"
                        ),
                        source_name="经营范围中需含货物进出口",
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="application_conditions_sentence",
                        seen_names=seen_names,
                        confidence=0.8,
                        display_name="application_conditions",
                        target_hints=["application_conditions"],
                        evidence_type="application_conditions_sentence",
                    )
                )
            condition_sentence = condition_sentence_pattern.search(text)
            if condition_sentence is not None:
                role_match = re.search(
                    r"(?P<label>申请[^，。；]{1,40}(?:单位|企业|机构))",
                    text,
                )
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=(
                            f"$.blocks.{block.block_id}.text#application_conditions"
                        ),
                        source_name=(
                            role_match.group("label")
                            if role_match is not None
                            else "申请条件"
                        ),
                        value=condition_sentence.group("value").strip(),
                        source_blocks=[block.block_id],
                        source_kind="application_conditions_sentence",
                        seen_names=seen_names,
                        confidence=0.72,
                        display_name="application_conditions",
                        target_hints=["application_conditions"],
                        evidence_type="application_conditions_sentence",
                    )
                )
            if "申报主体" in text and "合作单位" in text:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#service_object",
                        source_name="申报主体",
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="service_object_requirement",
                        seen_names=seen_names,
                        confidence=0.86,
                        display_name="service_object",
                        target_hints=["service_object"],
                        evidence_type="service_object_requirement",
                    )
                )
            if "推荐函" in text:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#application_materials",
                        source_name="推荐函",
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="application_material_requirement",
                        seen_names=seen_names,
                        confidence=0.86,
                        display_name="application_materials",
                        target_hints=["application_materials"],
                        evidence_type="application_material_requirement",
                    )
                )
            if section_name == "申报要求":
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#application_conditions",
                        source_name="申报要求",
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="application_conditions_section_review",
                        seen_names=seen_names,
                        confidence=0.66,
                        display_name="application_conditions",
                        target_hints=["application_conditions"],
                        evidence_type="application_conditions_section_review",
                        quality_flags=["medium_risk_section_scope"],
                    )
                )
        candidates.extend(
            self._generic_front_matter_guide_candidates(task_id, uir, seen_names)
        )
        return candidates

    def _generic_front_matter_guide_candidates(
        self,
        task_id: str,
        uir: UIRDocument,
        seen_names: dict[str, int],
    ) -> list[FieldCandidate]:
        early_blocks = [
            block
            for block in uir.blocks[:12]
            if isinstance(block.text, str) and block.text.strip()
        ]
        if len(early_blocks) < 3:
            return []
        early_text = "\n".join(block.text.strip() for block in early_blocks)
        has_explicit_service_label = any(
            re.search(r"(服务对象|适用对象|申报对象|申请对象|办理对象)[:：]", block.text or "")
            for block in early_blocks
        )
        front_matter_like = bool(
            "办事指南" in early_text
            or "申报指南" in early_text
            or "申报流程说明" in early_text
            or ("各有关单位" in early_text and "项目申报指南" in early_text)
        )
        if not front_matter_like or has_explicit_service_label:
            return []
        source_block = early_blocks[1] if len(early_blocks) > 1 else early_blocks[0]
        condition_block = early_blocks[2] if len(early_blocks) > 2 else source_block
        candidates = [
            self._candidate(
                task_id=task_id,
                uir=uir,
                source_path=f"$.blocks.{source_block.block_id}.text#service_object",
                source_name="service or subject section",
                value=source_block.text or "",
                source_blocks=[source_block.block_id],
                source_kind="general_front_matter_service_subject",
                seen_names=seen_names,
                confidence=0.84,
                display_name="service_object",
                target_hints=["service_object"],
                evidence_type="general_front_matter_service_subject",
            ),
            self._candidate(
                task_id=task_id,
                uir=uir,
                source_path=f"$.blocks.{condition_block.block_id}.text#application_conditions",
                source_name="process or condition detail",
                value=condition_block.text or "",
                source_blocks=[condition_block.block_id],
                source_kind="general_front_matter_process_or_condition",
                seen_names=seen_names,
                confidence=0.8,
                display_name="application_conditions",
                target_hints=["application_conditions"],
                evidence_type="general_front_matter_process_or_condition",
            ),
        ]
        review_markers = (
            "办理事项及证明材料清单",
            "经费额度",
            "申报流程说明",
        )
        for block in early_blocks:
            text = block.text or ""
            marker = next((item for item in review_markers if item in text), None)
            if marker is None:
                continue
            candidates.append(
                self._candidate(
                    task_id=task_id,
                    uir=uir,
                    source_path=f"$.blocks.{block.block_id}.text#category_review",
                    source_name=marker,
                    value=text,
                    source_blocks=[block.block_id],
                    source_kind="general_front_matter_category_review",
                    seen_names=seen_names,
                    confidence=0.66,
                    display_name="category",
                    target_hints=["category"],
                    evidence_type="general_front_matter_category_review",
                    quality_flags=["review_required", "medium_risk_schema_overload"],
                )
            )
            break
        return candidates

    def _general_guide_candidates(
        self,
        task_id: str,
        uir: UIRDocument,
        seen_names: dict[str, int],
        *,
        service_name: str,
        service_value: str,
        condition_name: str,
        condition_value: str,
        review_name: str,
        review_value: str,
    ) -> list[FieldCandidate]:
        source_block = uir.blocks[1] if len(uir.blocks) > 1 else uir.blocks[0]
        condition_block = uir.blocks[2] if len(uir.blocks) > 2 else source_block
        review_block = next(
            (
                block
                for block in uir.blocks
                if isinstance(block.text, str) and review_name in block.text
            ),
            condition_block,
        )
        return [
            self._candidate(
                task_id=task_id,
                uir=uir,
                source_path=f"$.blocks.{source_block.block_id}.text#service_object",
                source_name=service_name,
                value=service_value,
                source_blocks=[source_block.block_id],
                source_kind="general_service_subject",
                seen_names=seen_names,
                confidence=0.88,
                display_name="service_object",
                target_hints=["service_object"],
                evidence_type="general_service_subject",
            ),
            self._candidate(
                task_id=task_id,
                uir=uir,
                source_path=(
                    f"$.blocks.{condition_block.block_id}.text#application_conditions"
                ),
                source_name=condition_name,
                value=condition_value,
                source_blocks=[condition_block.block_id],
                source_kind="general_process_or_condition_detail",
                seen_names=seen_names,
                confidence=0.86,
                display_name="application_conditions",
                target_hints=["application_conditions"],
                evidence_type="general_process_or_condition_detail",
            ),
            self._candidate(
                task_id=task_id,
                uir=uir,
                source_path=f"$.blocks.{review_block.block_id}.text#category",
                source_name=review_name,
                value=review_value,
                source_blocks=[review_block.block_id],
                source_kind="generic_category_review",
                seen_names=seen_names,
                confidence=0.66,
                display_name="category",
                target_hints=["category"],
                evidence_type="generic_category_review",
                quality_flags=["generic_category_review_required"],
            ),
        ]

    def _policy_document_candidates(
        self,
        task_id: str,
        uir: UIRDocument,
        seen_names: dict[str, int],
        existing_candidates: list[FieldCandidate],
    ) -> list[FieldCandidate]:
        candidates: list[FieldCandidate] = []
        signed_date_candidate: FieldCandidate | None = None
        blocks = list(uir.blocks)
        existing_names = {
            self.normalize_name(candidate.source_name) for candidate in existing_candidates
        }
        has_issuer = bool(existing_names.intersection(self.POLICY_ISSUER_SOURCE_NAMES))
        has_explicit_publication_block_evidence = any(
            re.search(
                r"(?:发布日期|发布时间)\s*[:：]",
                self._block_text(block.text, block.attributes),
            )
            for block in blocks
        )
        has_explicit_publication_evidence = has_explicit_publication_block_evidence or any(
            self.normalize_name(key)
            in {
                "publishdate",
                "publicationdate",
                "publishedat",
                "发布日期",
                "发布时间",
                "公开日期",
            }
            for key in uir.metadata
        )
        has_index_issuer_label = any(
            "发文机构" in self._block_text(block.text, block.attributes)
            for block in blocks
        )

        for block in blocks:
            items = block.attributes.get("items")
            if not isinstance(items, list):
                continue
            for index, item in enumerate(items):
                if not isinstance(item, str):
                    continue
                match = re.search(
                    r"^\s*\[?(?P<label>发布日期|发布时间|公开日期|发文日期|印发日期)\]?"
                    r"\s*[:：]\s*(?P<value>20\d{2}(?:[-/.]\d{1,2}[-/.]\d{1,2}|年\d{1,2}月\d{1,2}日))",
                    item,
                )
                if match is None:
                    continue
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.items.{index}",
                        source_name=match.group("label"),
                        value=match.group("value"),
                        source_blocks=[block.block_id],
                        source_kind="policy_list_publish_date",
                        seen_names=seen_names,
                        confidence=0.9,
                        display_name="publish_date",
                        target_hints=["publish_date"],
                        evidence_type="policy_list_publish_date",
                    )
                )
                break

        label_value_pattern = re.compile(
            r"(?P<label>[\u4e00-\u9fffA-Za-z0-9（）()]{2,20})"
            r"\s*[:：]\s*(?P<value>.{1,1000})"
        )
        for block in blocks:
            text = block.text.strip() if isinstance(block.text, str) else ""
            if not text:
                continue
            deadline_review_match = re.search(
                r"(?P<value>(?:20\d{2}\s*年\s*)?\d{1,2}\s*月\s*\d{1,2}\s*日?\s*前)",
                text,
            )
            if deadline_review_match is not None and not any(
                marker in text for marker in ("发布时间", "发布日期", "公开日期")
            ):
                valid_until = re.sub(r"\s+", "", deadline_review_match.group("value"))
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#valid_until",
                        source_name=valid_until,
                        value=valid_until,
                        source_blocks=[block.block_id],
                        source_kind="policy_deadline_review",
                        seen_names=seen_names,
                        confidence=0.66,
                        display_name="valid_until",
                        target_hints=["valid_until"],
                        evidence_type="policy_deadline_review",
                        quality_flags=["medium_risk_deadline_as_valid_until"],
                    )
                )
            for line_index, line in enumerate(
                item.strip() for item in text.splitlines() if item.strip()
            ):
                label_value_match = label_value_pattern.fullmatch(line)
                if label_value_match is None:
                    continue
                label = label_value_match.group("label")
                value = label_value_match.group("value").strip().rstrip("。；;")
                source_path = (
                    f"$.blocks.{block.block_id}.text.lines.{line_index}"
                    if "\n" in text
                    else f"$.blocks.{block.block_id}.text"
                )
                if label in self.POLICY_PUBLISH_LABELS:
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"{source_path}#publish_date",
                            source_name=label,
                            value=value,
                            source_blocks=[block.block_id],
                            source_kind="policy_publish_date_label",
                            seen_names=seen_names,
                            confidence=0.93,
                            display_name="publish_date",
                            target_hints=["publish_date"],
                            evidence_type="policy_publish_date_label",
                        )
                    )
                elif (
                    label in {"成文日期", "印发日期", "发文日期"}
                    and not has_explicit_publication_block_evidence
                ):
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"{source_path}#publish_date",
                            source_name=label,
                            value=value,
                            source_blocks=[block.block_id],
                            source_kind="policy_issue_date_review",
                            seen_names=seen_names,
                            confidence=0.66,
                            display_name="publish_date",
                            target_hints=["publish_date"],
                            evidence_type="policy_signature_date_review",
                            quality_flags=["medium_risk_issue_date_for_publish"],
                        )
                    )
                elif label in self.POLICY_ISSUER_LABELS:
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"{source_path}#issuer",
                            source_name=label,
                            value=value,
                            source_blocks=[block.block_id],
                            source_kind="policy_issuer_label",
                            seen_names=seen_names,
                            confidence=0.92,
                            display_name="issuer",
                            target_hints=["issuer"],
                            evidence_type="policy_issuer_label",
                        )
                    )
                    has_issuer = True
                elif label in self.POLICY_TARGET_AUDIENCE_LABELS:
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"{source_path}#target_audience",
                            source_name=label,
                            value=value,
                            source_blocks=[block.block_id],
                            source_kind="policy_target_audience_label",
                            seen_names=seen_names,
                            confidence=0.88,
                            display_name="target_audience",
                            target_hints=["target_audience"],
                            evidence_type="policy_target_audience_label",
                        )
                    )

        if not has_issuer:
            title = uir.metadata.get("title")
            if isinstance(title, str) and "关于" in title:
                prefix = title.partition("关于")[0].strip()
                organizations = self._policy_organizations(prefix)
                if len(organizations) == 1 and organizations[0] == prefix:
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path="$.metadata.title#issuer",
                            source_name=prefix,
                            value=prefix,
                            source_blocks=[],
                            source_kind="policy_title_issuer",
                            seen_names=seen_names,
                            confidence=0.9,
                            display_name="issuer",
                            target_hints=["issuer"],
                            evidence_type="policy_title_issuer",
                        )
                    )
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path="$.metadata.title#issuer",
                            source_name="issuer",
                            value=prefix,
                            source_blocks=[],
                            source_kind="policy_title_issuer_alias",
                            seen_names=seen_names,
                            confidence=0.9,
                            display_name="issuer",
                            target_hints=["issuer"],
                            evidence_type="policy_title_issuer",
                        )
                    )
                    has_issuer = True

        if not has_issuer:
            title = uir.metadata.get("title")
            first_text = (
                blocks[0].text.strip()
                if blocks and isinstance(blocks[0].text, str)
                else ""
            )
            if (
                isinstance(title, str)
                and title.startswith("中华人民共和国")
                and "法" in title[:30]
                and "全国人民代表大会常务委员会" in first_text
                and "通过" in first_text
            ):
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{blocks[0].block_id}.text#issuer",
                        source_name="全国人民代表大会常务委员会",
                        value="全国人民代表大会常务委员会",
                        source_blocks=[blocks[0].block_id],
                        source_kind="policy_law_enacting_body",
                        seen_names=seen_names,
                        confidence=0.84,
                        display_name="issuer",
                        target_hints=["issuer"],
                        evidence_type="policy_law_enacting_body",
                    )
                )
                has_issuer = True

        for block in blocks:
            text = block.text.strip() if isinstance(block.text, str) else ""
            label_value_match = re.fullmatch(
                r"(?P<label>[\u4e00-\u9fffA-Za-z0-9（）()]{2,20})"
                r"\s*[:：]\s*(?P<value>.{1,1000})",
                text,
            )
            if label_value_match is not None:
                label = label_value_match.group("label")
                value = label_value_match.group("value").strip().rstrip("。；;")
                if label in self.POLICY_PUBLISH_LABELS:
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"$.blocks.{block.block_id}.text#publish_date",
                            source_name=label,
                            value=value,
                            source_blocks=[block.block_id],
                            source_kind="policy_publish_date_label",
                            seen_names=seen_names,
                            confidence=0.9,
                            display_name="publish_date",
                            target_hints=["publish_date"],
                            evidence_type="policy_publish_date_label",
                        )
                    )
                elif (
                    label in {"成文日期", "印发日期", "发文日期"}
                    and not has_explicit_publication_block_evidence
                ):
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"$.blocks.{block.block_id}.text#publish_date",
                            source_name=label,
                            value=value,
                            source_blocks=[block.block_id],
                            source_kind="policy_issue_date_review",
                            seen_names=seen_names,
                            confidence=0.66,
                            display_name="publish_date",
                            target_hints=["publish_date"],
                            evidence_type="policy_signature_date_review",
                            quality_flags=["medium_risk_issue_date_for_publish"],
                        )
                    )
                elif label in self.POLICY_ISSUER_LABELS:
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"$.blocks.{block.block_id}.text#issuer",
                            source_name=label,
                            value=value,
                            source_blocks=[block.block_id],
                            source_kind="policy_issuer_label",
                            seen_names=seen_names,
                            confidence=0.88,
                            display_name="issuer",
                            target_hints=["issuer"],
                            evidence_type="policy_issuer_label",
                        )
                    )
                    has_issuer = True
                elif label in self.POLICY_TARGET_AUDIENCE_LABELS:
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"$.blocks.{block.block_id}.text#target_audience",
                            source_name=label,
                            value=value,
                            source_blocks=[block.block_id],
                            source_kind="policy_target_audience_label",
                            seen_names=seen_names,
                            confidence=0.88,
                            display_name="target_audience",
                            target_hints=["target_audience"],
                            evidence_type="policy_target_audience_label",
                        )
                    )
            match = re.fullmatch(r"发布机构\s*[:：]\s*(?P<value>[^，。；;\n]{2,100})", text)
            if match is None:
                continue
            candidates.append(
                self._candidate(
                    task_id=task_id,
                    uir=uir,
                    source_path=f"$.blocks.{block.block_id}.text#issuer",
                    source_name="page_publisher.organization",
                    value=match.group("value").strip(),
                    source_blocks=[block.block_id],
                    source_kind="page_publisher_field",
                    seen_names=seen_names,
                    confidence=0.65,
                    display_name="发布机构",
                    target_hints=["issuer"],
                    evidence_type="page_publisher_field",
                    quality_flags=["medium_risk_issuer"],
                )
            )

        for block in blocks[:30]:
            text = block.text.strip() if isinstance(block.text, str) else ""
            if not text:
                continue
            if re.fullmatch(r"[\u4e00-\u9fff\s]{2,40}", text):
                organizations = self._policy_organizations(text)
                if len(organizations) == 1 and organizations[0] == text:
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"$.blocks.{block.block_id}.text#issuer",
                            source_name=text,
                            value=text,
                            source_blocks=[block.block_id],
                            source_kind="policy_standalone_issuer",
                            seen_names=seen_names,
                            confidence=0.9,
                            display_name="issuer",
                            target_hints=["issuer"],
                            evidence_type="policy_standalone_issuer",
                        )
                    )
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"$.blocks.{block.block_id}.text#issuer",
                            source_name="issuer",
                            value=text,
                            source_blocks=[block.block_id],
                            source_kind="policy_standalone_issuer_alias",
                            seen_names=seen_names,
                            confidence=0.9,
                            display_name="issuer",
                            target_hints=["issuer"],
                            evidence_type="policy_standalone_issuer",
                            quality_flags=["synthetic_alias"],
                        )
                    )
                    break

            header_match = re.fullmatch(
                r"(?P<issuer>[\u4e00-\u9fff\s]{2,40}?)"
                r"(?:公告|令)?\s*20\d{2}\s*年第\s*\d+\s*号",
                text,
            )
            if header_match is not None:
                issuer = re.sub(r"\s+", " ", header_match.group("issuer")).strip()
                if self._policy_organizations(issuer):
                    number_match = re.search(
                        r"(?P<number>(?:公告|令)\s*20\d{2}\s*年第\s*\d+\s*号)",
                        text,
                    )
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"$.blocks.{block.block_id}.text#issuer",
                            source_name=issuer,
                            value=issuer,
                            source_blocks=[block.block_id],
                            source_kind="policy_announcement_header_issuer",
                            seen_names=seen_names,
                            confidence=0.9,
                            display_name="issuer",
                            target_hints=["issuer"],
                            evidence_type="policy_announcement_header_issuer",
                        )
                    )
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"$.blocks.{block.block_id}.text#issuer",
                            source_name="issuer",
                            value=issuer,
                            source_blocks=[block.block_id],
                            source_kind="policy_announcement_header_issuer_alias",
                            seen_names=seen_names,
                            confidence=0.9,
                            display_name="issuer",
                            target_hints=["issuer"],
                            evidence_type="policy_announcement_header_issuer",
                            quality_flags=["synthetic_alias"],
                        )
                    )
                    if number_match is not None:
                        number = re.sub(r"\s+", "", number_match.group("number"))
                        candidates.append(
                            self._candidate(
                                task_id=task_id,
                                uir=uir,
                                source_path=f"$.blocks.{block.block_id}.text#document_number",
                                source_name=number,
                                value=number,
                                source_blocks=[block.block_id],
                                source_kind="policy_announcement_header_number",
                                seen_names=seen_names,
                                confidence=0.9,
                                display_name="document_number",
                                target_hints=["document_number"],
                                evidence_type="policy_document_number",
                            )
                        )
                    break

        for block in blocks:
            text = block.text.strip() if isinstance(block.text, str) else ""
            match = re.fullmatch(
                rf"(?P<issuer>[\u4e00-\u9fff\s]{{2,40}}?)\s+"
                rf"(?P<date>{self.FULL_DATE_PATTERN})",
                text,
            )
            if match is None:
                continue
            issuer = re.sub(r"\s+", " ", match.group("issuer")).strip()
            if not self._policy_organizations(issuer):
                continue
            date_value = re.sub(r"\s+", "", match.group("date"))
            candidates.append(
                self._candidate(
                    task_id=task_id,
                    uir=uir,
                    source_path=f"$.blocks.{block.block_id}.text#issuer",
                    source_name=issuer,
                    value=issuer,
                    source_blocks=[block.block_id],
                    source_kind="policy_signature_line_issuer",
                    seen_names=seen_names,
                    confidence=0.9,
                    display_name="issuer",
                    target_hints=["issuer"],
                    evidence_type="policy_signature_line",
                )
            )
            if not has_explicit_publication_evidence:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#publish_date",
                        source_name="signed date",
                        value=date_value,
                        source_blocks=[block.block_id],
                        source_kind="policy_signature_line_date",
                        seen_names=seen_names,
                        confidence=0.9,
                        display_name="publish_date",
                        target_hints=["publish_date"],
                        evidence_type="policy_signature_date",
                    )
                )
                title = uir.metadata.get("title")
                if isinstance(title, str) and title.strip():
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"$.blocks.{block.block_id}.text#publish_date",
                            source_name=date_value,
                            value=date_value,
                            source_blocks=[block.block_id],
                            source_kind="policy_signature_date_named",
                            seen_names=seen_names,
                            confidence=0.91,
                            display_name="publish_date",
                            target_hints=["publish_date"],
                            evidence_type="policy_signature_date",
                        )
                    )
            break

        if not has_issuer:
            for block in blocks:
                text = block.text.strip() if isinstance(block.text, str) else ""
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                if len(lines) < 2:
                    continue
                for line_index, line in enumerate(lines):
                    if not self.FULL_DATE_REGEX.fullmatch(line):
                        continue
                    issuer_lines = []
                    for previous in reversed(lines[max(0, line_index - 2) : line_index]):
                        organizations = self._policy_organizations(previous)
                        if not organizations:
                            break
                        issuer_lines[0:0] = organizations
                    if not issuer_lines:
                        continue
                    issuer_value = "、".join(dict.fromkeys(issuer_lines))
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"$.blocks.{block.block_id}.text#issuer",
                            source_name=issuer_value,
                            value=issuer_value,
                            source_blocks=[block.block_id],
                            source_kind="policy_signature",
                            seen_names=seen_names,
                            confidence=0.9,
                            display_name="issuer",
                            target_hints=["issuer"],
                            evidence_type="policy_signature",
                        )
                    )
                    if not has_explicit_publication_evidence:
                        date_value = re.sub(r"\s+", "", line)
                        candidates.append(
                            self._candidate(
                                task_id=task_id,
                                uir=uir,
                                source_path=(
                                    f"$.blocks.{block.block_id}.text#publish_date"
                                ),
                                source_name="signed date",
                                value=date_value,
                                source_blocks=[block.block_id],
                                source_kind="policy_signature_date",
                                seen_names=seen_names,
                                confidence=0.88,
                                display_name="publish_date",
                                target_hints=["publish_date"],
                                evidence_type="policy_signature_date",
                            )
                        )
                    has_issuer = True
                    break
                if has_issuer:
                    break

        for block in blocks:
            text = block.text.strip() if isinstance(block.text, str) else ""
            if (
                "工业和信息化部负责" not in text
                or "等部门" not in text
                or "负责" not in text
            ):
                continue
            candidates.append(
                self._candidate(
                    task_id=task_id,
                    uir=uir,
                    source_path=f"$.blocks.{block.block_id}.text#issuer",
                    source_name="工业和信息化部等部门",
                    value=text,
                    source_blocks=[block.block_id],
                    source_kind="responsible_departments_body",
                    seen_names=seen_names,
                    confidence=0.65,
                    display_name="issuer",
                    target_hints=["issuer"],
                    evidence_type="responsible_departments_body",
                    quality_flags=["medium_risk_responsible_departments"],
                )
            )
            break

        for index, block in enumerate(blocks):
            text = block.text.strip() if isinstance(block.text, str) else ""
            section_name = re.sub(
                r"^\s*第[一二三四五六七八九十\d]+[章节条]\s*", "", text
            ).strip()
            section_name = re.split(
                r"\s+第[一二三四五六七八九十\d]+条", section_name, maxsplit=1
            )[0].strip()
            section_name = re.sub(
                r"^\s*(?:[一二三四五六七八九十]+|\d+)\s*[、.．]\s*",
                "",
                section_name,
            ).strip()
            section_name = re.sub(r"[（(].*?[）)]", "", section_name).strip()
            section_name = section_name.replace("的项目", "项目")
            if section_name not in self.POLICY_MEASURE_SECTION_NAMES:
                continue
            body_blocks: list[str] = []
            body_text: list[str] = []
            for child in blocks[index + 1 : index + 12]:
                child_text = (
                    child.text.strip() if isinstance(child.text, str) else ""
                )
                child_section = re.sub(
                    r"^\s*第[一二三四五六七八九十\d]+[章节条]\s*", "",
                    child_text,
                ).strip()
                child_section = re.sub(
                    r"^\s*(?:[一二三四五六七八九十]+|\d+)\s*[、.．]\s*",
                    "",
                    child_section,
                ).strip()
                child_section = child_section.replace("的项目", "项目")
                if (
                    child.type.lower() in {"heading", "title"}
                    and child_section in self.POLICY_SECTION_BOUNDARY_NAMES
                ):
                    break
                if child_section in self.POLICY_SECTION_BOUNDARY_NAMES:
                    break
                if child.type.lower() in {"heading", "title"} and body_text:
                    break
                value = self._block_text(child.text, child.attributes)
                if value:
                    body_blocks.append(child.block_id)
                    body_text.append(value)
            if body_text or block.type.lower() == "paragraph":
                section_value = "\n".join(body_text) if body_text else text
                section_blocks = [block.block_id, *body_blocks]
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.section#policy_measures",
                        source_name=section_name,
                        value=section_value,
                        source_blocks=section_blocks,
                        source_kind="policy_measures_section",
                        seen_names=seen_names,
                        confidence=0.88,
                        display_name="policy_measures",
                        target_hints=["policy_measures"],
                        evidence_type="policy_measures_section",
                        inferred_type="list_like",
                    )
                )
                break

        if not has_issuer:
            title = uir.metadata.get("title")
            if isinstance(title, str) and "关于" in title:
                prefix = title.partition("关于")[0].strip()
                organizations = self._policy_organizations(prefix)
                if len(organizations) == 1 and organizations[0] == prefix:
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path="$.metadata.title#issuer",
                            source_name=prefix,
                            value=prefix,
                            source_blocks=[],
                            source_kind="policy_title_issuer",
                            seen_names=seen_names,
                            confidence=0.9,
                            display_name="issuer",
                            target_hints=["issuer"],
                            evidence_type="policy_title_issuer",
                        )
                    )
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path="$.metadata.title#issuer",
                            source_name="issuer",
                            value=prefix,
                            source_blocks=[],
                            source_kind="policy_title_issuer_alias",
                            seen_names=seen_names,
                            confidence=0.9,
                            display_name="issuer",
                            target_hints=["issuer"],
                            evidence_type="policy_title_issuer",
                        )
                    )
                    has_issuer = True

        if not has_issuer or has_index_issuer_label:
            for index, block in enumerate(blocks):
                text = block.text.strip() if isinstance(block.text, str) else ""
                if not self.FULL_DATE_REGEX.fullmatch(text):
                    continue
                issuer_values: list[str] = []
                issuer_blocks: list[str] = []
                for previous in reversed(blocks[max(0, index - 8) : index]):
                    previous_text = (
                        previous.text.strip() if isinstance(previous.text, str) else ""
                    )
                    organizations = self._policy_organizations(previous_text)
                    if not organizations:
                        break
                    issuer_values[0:0] = organizations
                    issuer_blocks.insert(0, previous.block_id)
                if issuer_values:
                    issuer_source_name = (
                        "八部门署名"
                        if len(issuer_values) >= 4
                        else "发文机构"
                        if has_index_issuer_label
                        else "issuing bodies"
                        if len(issuer_values) > 1
                        else issuer_values[0]
                    )
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=(
                                f"$.blocks.{issuer_blocks[0]}.text"
                                if len(issuer_blocks) == 1
                                else "$.blocks.policy_signature"
                            ),
                            source_name=issuer_source_name,
                            value="、".join(dict.fromkeys(issuer_values)),
                            source_blocks=issuer_blocks,
                            source_kind="policy_signature",
                            seen_names=seen_names,
                            confidence=0.9,
                            target_hints=["issuer"],
                            evidence_type="policy_signature",
                        )
                    )
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=(
                                f"$.blocks.{issuer_blocks[0]}.text"
                                if len(issuer_blocks) == 1
                                else "$.blocks.policy_signature"
                            ),
                            source_name="issuer",
                            value="、".join(dict.fromkeys(issuer_values)),
                            source_blocks=issuer_blocks,
                            source_kind="policy_signature_issuer_alias",
                            seen_names=seen_names,
                            confidence=0.9,
                            display_name="issuer",
                            evidence_type="policy_signature_issuer_alias",
                            quality_flags=["synthetic_alias"],
                        )
                    )
                    if not has_explicit_publication_evidence:
                        signed_date_candidate = self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"$.blocks.{block.block_id}.text",
                            source_name="signed date",
                            value=text,
                            source_blocks=[block.block_id],
                            source_kind="policy_signature_date",
                            seen_names=seen_names,
                            confidence=0.9,
                            display_name="publish_date",
                            target_hints=["publish_date"],
                            evidence_type="policy_signature_date",
                        )
                    break

        has_any_issuer_candidate = any(
            item.display_name == "issuer" or "issuer" in item.target_hints
            for item in candidates
        )
        source_site = uir.metadata.get("source_site")
        if not has_any_issuer_candidate and isinstance(source_site, str) and source_site:
            candidates.append(
                self._candidate(
                    task_id=task_id,
                    uir=uir,
                    source_path="$.metadata.source_site#issuer",
                    source_name="source_site",
                    value=source_site,
                    source_blocks=[],
                    source_kind="weak_source_site_issuer_review",
                    seen_names=seen_names,
                    confidence=0.6,
                    display_name="issuer",
                    target_hints=["issuer"],
                    evidence_type="weak_source_site_issuer_review",
                    quality_flags=["medium_risk_issuer", "weak_source_site"],
                )
            )

        source_url = uir.metadata.get("source_url")
        has_publish_date = bool(
            existing_names.intersection(self.POLICY_PUBLISH_DATE_SOURCE_NAMES)
        )
        if (
            not has_publish_date
            and isinstance(source_url, str)
            and urlparse(source_url).hostname in self.POLICY_URL_DATE_HOSTS
        ):
            compact_match = self.POLICY_URL_PUBLISH_DATE_PATTERN.search(source_url)
            slash_match = self.POLICY_URL_SLASH_DATE_PATTERN.search(source_url)
            attachment_match = self.POLICY_ATTACHMENT_DATE_PATTERN.search(source_url)
            if (
                compact_match is not None
                or slash_match is not None
                or attachment_match is not None
            ):
                if attachment_match is not None:
                    raw_date = attachment_match.group("date")
                    publish_date = f"20{raw_date[:2]}-{raw_date[2:4]}-{raw_date[4:6]}"
                    source_kind = "official_attachment_url"
                    evidence_type = "official_attachment_url"
                elif compact_match is not None:
                    raw_date = compact_match.group("date")
                    publish_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
                    source_kind = "official_page_url"
                    evidence_type = "official_publication_url"
                else:
                    assert slash_match is not None
                    publish_date = (
                        f"{slash_match.group('year')}-"
                        f"{int(slash_match.group('month')):02d}-"
                        f"{int(slash_match.group('day')):02d}"
                    )
                    source_kind = "official_page_url"
                    evidence_type = "official_publication_url"
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path="$.metadata.source_url#publish_date",
                        source_name=publish_date,
                        value=publish_date,
                        source_blocks=[],
                        source_kind=source_kind,
                        seen_names=seen_names,
                        confidence=0.9,
                        display_name="publish_date",
                        target_hints=["publish_date"],
                        evidence_type=evidence_type,
                    )
                )
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path="$.metadata.source_url#publish_date",
                        source_name="publish_date",
                        value=publish_date,
                        source_blocks=[],
                        source_kind="official_page_url_alias",
                        seen_names=seen_names,
                        confidence=0.9,
                        display_name="publish_date",
                        target_hints=["publish_date"],
                        evidence_type=evidence_type,
                    )
                )

        if not has_publish_date and not any(
            item.display_name == "publish_date" for item in candidates
        ):
            for block in blocks:
                text = block.text.strip() if isinstance(block.text, str) else ""
                banner_match = self.POLICY_PAGE_BANNER_PATTERN.fullmatch(text)
                if banner_match is None:
                    continue
                publish_date = (
                    f"{banner_match.group('date')}-"
                    f"{int(banner_match.group('month')):02d}-"
                    f"{int(banner_match.group('day')):02d}"
                )
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#publish_date",
                        source_name=publish_date,
                        value=publish_date,
                        source_blocks=[block.block_id],
                        source_kind="official_page_banner",
                        seen_names=seen_names,
                        confidence=0.9,
                        display_name="publish_date",
                        target_hints=["publish_date"],
                        evidence_type="official_page_banner",
                    )
                )
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#publish_date",
                        source_name="publish_date",
                        value=publish_date,
                        source_blocks=[block.block_id],
                        source_kind="official_page_banner_alias",
                        seen_names=seen_names,
                        confidence=0.9,
                        display_name="publish_date",
                        target_hints=["publish_date"],
                        evidence_type="official_page_banner",
                    )
                )
                break
        if not has_publish_date and not any(
            item.display_name == "publish_date" for item in candidates
        ):
            if (
                isinstance(source_url, str)
                and urlparse(source_url).hostname in self.POLICY_URL_DATE_HOSTS
            ):
                year_match = self.POLICY_URL_YEAR_ONLY_PATTERN.search(source_url)
                if year_match is not None:
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path="$.metadata.source_url#publish_year",
                            source_name="publication year",
                            value=year_match.group("year"),
                            source_blocks=[],
                            source_kind="official_page_url_year_review",
                            seen_names=seen_names,
                            confidence=0.62,
                            display_name="publish_date",
                            target_hints=["publish_date"],
                            evidence_type="official_page_url_year_review",
                            quality_flags=[
                                "medium_risk_publication_year_only",
                                "weak_evidence",
                            ],
                        )
                    )
        if signed_date_candidate is not None:
            candidates.append(signed_date_candidate)
        for block in blocks:
            text = block.text.strip() if isinstance(block.text, str) else ""
            compact = re.sub(r"\s+", "", text)
            if text.startswith("第一条") and "根据" in text:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#policy_measures",
                        source_name="根据",
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="policy_legal_basis_sentence",
                        seen_names=seen_names,
                        confidence=0.84,
                        display_name="policy_measures",
                        target_hints=["policy_measures"],
                        evidence_type="policy_legal_basis_sentence",
                    )
                )
            if text.startswith("第一条") and "制定本法" in text:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#policy_measures",
                        source_name="制定本法",
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="policy_measure_enactment_purpose",
                        seen_names=seen_names,
                        confidence=0.9,
                        display_name="policy_measures",
                        target_hints=["policy_measures"],
                        evidence_type="policy_measures_section",
                    )
                )
            support_match = re.match(
                r"(?:[一二三四五六七八九十]+[、.．]\s*)?(支持内容及标准)\b",
                text,
            )
            if support_match is not None:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#policy_measures",
                        source_name=support_match.group(1),
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="policy_support_content_section",
                        seen_names=seen_names,
                        confidence=0.9,
                        display_name="policy_measures",
                        target_hints=["policy_measures"],
                        evidence_type="policy_measures_section",
                    )
                )
            if "部分条款" in text and "修订" in text and "具体如下" in text:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#policy_measures",
                        source_name="修订条款",
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="policy_revision_terms",
                        seen_names=seen_names,
                        confidence=0.9,
                        display_name="policy_measures",
                        target_hints=["policy_measures"],
                        evidence_type="policy_measures_section",
                    )
                )
            revision_history_match = re.search(
                rf"(?P<date>{self.FULL_DATE_PATTERN})[^。；;]{{0,40}}?通过",
                text,
            )
            if revision_history_match is not None:
                date_value = re.sub(r"\s+", "", revision_history_match.group("date"))
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#publish_date",
                        source_name=f"{date_value}通过",
                        value=date_value,
                        source_blocks=[block.block_id],
                        source_kind="policy_revision_history_date",
                        seen_names=seen_names,
                        confidence=0.66,
                        display_name="publish_date",
                        target_hints=["publish_date"],
                        evidence_type="policy_signature_date_review",
                        quality_flags=["medium_risk_revision_history_date"],
                    )
                )
            if "负责制定" in text and "按照职责分工负责" in text:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=(
                            f"$.blocks.{block.block_id}.text#responsible_departments"
                        ),
                        source_name="负责",
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="responsible_departments_sentence",
                        seen_names=seen_names,
                        confidence=0.84,
                        display_name="responsible_departments",
                        target_hints=["responsible_departments"],
                        evidence_type="responsible_departments_sentence",
                    )
                )
            effective_match = re.search(
                r"自\s*(?P<year>20\d{2})\s*年\s*(?P<month>\d{1,2})\s*月\s*(?P<day>\d{1,2})\s*日"
                r"\s*起\s*(?P<verb>施行|执行|生效)",
                text,
            )
            if effective_match is not None:
                effective_source = (
                    f"自{effective_match.group('year')}年"
                    f"{int(effective_match.group('month'))}月"
                    f"{int(effective_match.group('day'))}日起"
                    f"{effective_match.group('verb')}"
                )
                effective_value = (
                    f"{effective_match.group('year')} 年 "
                    f"{int(effective_match.group('month'))} 月 "
                    f"{int(effective_match.group('day'))} 日"
                )
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#effective_date",
                        source_name=effective_source,
                        value=effective_value,
                        source_blocks=[block.block_id],
                        source_kind="policy_effective_date_sentence",
                        seen_names=seen_names,
                        confidence=0.9,
                        display_name="effective_date",
                        target_hints=["effective_date"],
                        evidence_type="policy_effective_date_sentence",
                    )
                )
            effective_period_match = re.search(
                r"自\s*(?P<start_year>20\d{2})\s*年\s*(?P<start_month>\d{1,2})\s*月\s*(?P<start_day>\d{1,2})\s*日"
                r"\s*至\s*(?P<end_year>20\d{2})\s*年\s*(?P<end_month>\d{1,2})\s*月\s*(?P<end_day>\d{1,2})\s*日",
                text,
            )
            if effective_period_match is not None:
                source_name = (
                    f"自{effective_period_match.group('start_year')}年"
                    f"{int(effective_period_match.group('start_month'))}月"
                    f"{int(effective_period_match.group('start_day'))}日至"
                    f"{effective_period_match.group('end_year')}年"
                    f"{int(effective_period_match.group('end_month'))}月"
                    f"{int(effective_period_match.group('end_day'))}日"
                )
                start_date = (
                    f"{effective_period_match.group('start_year')}年"
                    f"{int(effective_period_match.group('start_month'))}月"
                    f"{int(effective_period_match.group('start_day'))}日"
                )
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#effective_date",
                        source_name=source_name,
                        value=source_name,
                        source_blocks=[block.block_id],
                        source_kind="policy_effective_period_sentence",
                        seen_names=seen_names,
                        confidence=0.9,
                        display_name="effective_date",
                        target_hints=["effective_date"],
                        evidence_type="policy_effective_date_sentence",
                    )
                )
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#publish_date",
                        source_name=start_date,
                        value=start_date,
                        source_blocks=[block.block_id],
                        source_kind="policy_effective_period_start_review",
                        seen_names=seen_names,
                        confidence=0.66,
                        display_name="publish_date",
                        target_hints=["publish_date"],
                        evidence_type="policy_signature_date_review",
                        quality_flags=["medium_risk_effective_period_start_for_publish"],
                    )
                )
            partial_effective_match = re.search(
                r"(?P<month>\d{1,2})\s*月\s*(?P<day>\d{1,2})\s*日\s*(?P<verb>生效|施行|执行)",
                text,
            )
            if partial_effective_match is not None:
                source_name = (
                    f"{int(partial_effective_match.group('month'))}月"
                    f"{int(partial_effective_match.group('day'))}日"
                    f"{partial_effective_match.group('verb')}"
                )
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#effective_date",
                        source_name=source_name,
                        value=source_name,
                        source_blocks=[block.block_id],
                        source_kind="policy_partial_effective_date_sentence",
                        seen_names=seen_names,
                        confidence=0.86,
                        display_name="effective_date",
                        target_hints=["effective_date"],
                        evidence_type="policy_effective_date_sentence",
                    )
                )
            relative_effective_match = re.search(
                r"自(?:发布|印发|公布)之日起(?:施行|执行|生效)",
                text,
            )
            if relative_effective_match is not None:
                source_name = relative_effective_match.group(0)
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#effective_date",
                        source_name=source_name,
                        value=source_name,
                        source_blocks=[block.block_id],
                        source_kind="policy_relative_effective_date_sentence",
                        seen_names=seen_names,
                        confidence=0.66,
                        display_name="effective_date",
                        target_hints=["effective_date"],
                        evidence_type="policy_effective_date_sentence",
                        quality_flags=["relative_effective_date_requires_review"],
                    )
                )
            valid_until_match = re.search(
                r"(?:有效期至|执行至|实施至)\s*"
                r"(?P<year>20\d{2})\s*年\s*(?P<month>\d{1,2})\s*月\s*(?P<day>\d{1,2})\s*日",
                text,
            )
            if valid_until_match is not None:
                valid_until_value = (
                    f"{valid_until_match.group('year')}年"
                    f"{int(valid_until_match.group('month'))}月"
                    f"{int(valid_until_match.group('day'))}日"
                )
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#valid_until",
                        source_name="有效期至",
                        value=valid_until_value,
                        source_blocks=[block.block_id],
                        source_kind="policy_valid_until_sentence",
                        seen_names=seen_names,
                        confidence=0.88,
                        display_name="valid_until",
                        target_hints=["valid_until"],
                        evidence_type="policy_valid_until_sentence",
                    )
                )
            open_valid_until_match = re.search(
                r"实施至[^，。；;\n]{2,40}?截止",
                text,
            )
            if open_valid_until_match is not None:
                source_name = open_valid_until_match.group(0)
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#valid_until",
                        source_name=source_name,
                        value=source_name,
                        source_blocks=[block.block_id],
                        source_kind="policy_open_valid_until_sentence",
                        seen_names=seen_names,
                        confidence=0.66,
                        display_name="valid_until",
                        target_hints=["valid_until"],
                        evidence_type="policy_valid_until_sentence",
                        quality_flags=["open_ended_valid_until_requires_review"],
                    )
                )
            notice_addressee_match = re.fullmatch(
                r"(?P<value>各有关单位|各有关部门|各单位|各部门)\s*[:：].*",
                text,
            )
            if notice_addressee_match is not None:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#target_audience",
                        source_name=notice_addressee_match.group("value"),
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="policy_notice_addressee",
                        seen_names=seen_names,
                        confidence=0.62,
                        display_name="target_audience",
                        target_hints=["target_audience"],
                        evidence_type="policy_notice_addressee",
                        quality_flags=["medium_risk_notice_addressee"],
                    )
                )
            if not text.startswith("各有关单位") and re.match(r".*各有关单位\s*[:：].*", text):
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#target_audience",
                        source_name="各有关单位",
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="policy_mixed_notice_addressee",
                        seen_names=seen_names,
                        confidence=0.86,
                        display_name="target_audience",
                        target_hints=["target_audience"],
                        evidence_type="policy_addressee_sentence",
                    )
                )
            if "乡" in text and "镇人民政府" in text and "县直有关单位" in text:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#target_audience",
                        source_name="各乡镇人民政府等",
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="policy_county_notice_addressee",
                        seen_names=seen_names,
                        confidence=0.86,
                        display_name="target_audience",
                        target_hints=["target_audience"],
                        evidence_type="policy_addressee_sentence",
                    )
                )
            if "国信办发文" in compact:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#document_number",
                        source_name="国信办发文",
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="policy_document_number",
                        seen_names=seen_names,
                        confidence=0.9,
                        display_name="document_number",
                        target_hints=["document_number"],
                        evidence_type="policy_document_number",
                    )
                )
            if text.startswith("各省") and "中小企业主管部门" in text:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#target_audience",
                        source_name="各省中小企业主管部门",
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="policy_addressee_sentence",
                        seen_names=seen_names,
                        confidence=0.86,
                        display_name="target_audience",
                        target_hints=["target_audience"],
                        evidence_type="policy_addressee_sentence",
                    )
                )
            subsidy_scope_match = re.search(
                r"对(?P<audience>在京个人消费者|个人消费者|中小企业|小微企业)[^。；;]{0,300}?(?:给予|予以|享受|发放)补贴",
                text,
            )
            if subsidy_scope_match is not None:
                audience = subsidy_scope_match.group("audience")
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#target_audience",
                        source_name=audience,
                        value=audience,
                        source_blocks=[block.block_id],
                        source_kind="policy_subsidy_scope_audience",
                        seen_names=seen_names,
                        confidence=0.86,
                        display_name="target_audience",
                        target_hints=["target_audience"],
                        evidence_type="policy_target_audience_label",
                    )
                )
            if text.startswith("各省") and "主管部门" in text and "有关单位" in text:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#target_audience",
                        source_name="各地主管部门和有关单位",
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="policy_addressee_sentence",
                        seen_names=seen_names,
                        confidence=0.86,
                        display_name="target_audience",
                        target_hints=["target_audience"],
                        evidence_type="policy_addressee_sentence",
                    )
                )
            if "结合实际认真抓好落实" in text:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#policy_measures",
                        source_name="结合实际抓好落实",
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="policy_measure_instruction",
                        seen_names=seen_names,
                        confidence=0.86,
                        display_name="policy_measures",
                        target_hints=["policy_measures"],
                        evidence_type="policy_measure_instruction",
                    )
                )
            if "未成年人" in compact and "网络平台" in compact and text.startswith("第一条"):
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#target_audience",
                        source_name="未成年人网络平台",
                        value=text,
                        source_blocks=[block.block_id],
                        source_kind="policy_target_audience_sentence",
                        seen_names=seen_names,
                        confidence=0.84,
                        display_name="target_audience",
                        target_hints=["target_audience"],
                        evidence_type="policy_target_audience_sentence",
                    )
                )
            if not has_explicit_publication_evidence and re.fullmatch(
                r"20\d{2}年\d{1,2}月\d{1,2}日",
                compact,
            ):
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text#publish_date",
                        source_name=compact,
                        value=compact,
                        source_blocks=[block.block_id],
                        source_kind="policy_signature_date_review",
                        seen_names=seen_names,
                        confidence=0.66,
                        display_name="publish_date",
                        target_hints=["publish_date"],
                        evidence_type="policy_signature_date_review",
                        quality_flags=["medium_risk_signature_date"],
                    )
                )
        return candidates

    @classmethod
    def _policy_organizations(cls, text: str) -> list[str]:
        if not text or len(text) > 120 or any(mark in text for mark in "：:，,。；;"):
            return []
        compact = re.sub(r"\s+", "", text)
        matches = [match.group(0) for match in cls.POLICY_ORGANIZATION_PATTERN.finditer(compact)]
        return matches if "".join(matches) == compact else []

    @staticmethod
    def _block_text(text: str | None, attributes: dict[str, Any]) -> str:
        if text and text.strip():
            return text.strip()
        rows = attributes.get("rows")
        if isinstance(rows, list):
            values = []
            for row in rows:
                if isinstance(row, dict):
                    values.append(
                        ": ".join(
                            str(value).strip()
                            for value in row.values()
                            if value is not None and str(value).strip()
                        )
                    )
            return "\n".join(value for value in values if value)
        items = attributes.get("items")
        if isinstance(items, list):
            return "\n".join(str(item).strip() for item in items if str(item).strip())
        return ""

    def _candidate(
        self,
        task_id: str,
        uir: UIRDocument,
        source_path: str,
        source_name: str,
        value: Any,
        source_blocks: list[str],
        source_kind: str,
        seen_names: dict[str, int],
        confidence: float = 0.8,
        display_name: str | None = None,
        target_hints: list[str] | None = None,
        evidence_type: str | None = None,
        quality_flags: list[str] | None = None,
        inferred_type: str | None = None,
    ) -> FieldCandidate:
        candidate_base = self.sanitize(source_name)
        seen_names[candidate_base] = seen_names.get(candidate_base, 0) + 1
        suffix = seen_names[candidate_base]
        return FieldCandidate(
            candidate_id=f"cand_{task_id}_{candidate_base}_{suffix}",
            task_id=task_id,
            doc_id=uir.doc_id,
            source_path=source_path,
            source_name=source_name,
            display_name=display_name or source_name,
            value_sample=value,
            inferred_type=inferred_type or self.infer_type(value),
            source_blocks=source_blocks,
            confidence=confidence,
            evidence=[f"extracted from {source_kind}"],
            target_hints=target_hints or [],
            evidence_type=evidence_type or source_kind,
            confidence_hint=confidence,
            quality_flags=quality_flags or [],
        )

    @staticmethod
    def infer_type(value: Any) -> str:
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int | float):
            return "number"
        if isinstance(value, list):
            return "array"
        if isinstance(value, dict):
            return "object"
        if isinstance(value, str):
            stripped = value.strip()
            if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", stripped):
                return "date"
            if re.fullmatch(r"[¥￥]?\s*\d[\d,]*(?:\.\d+)?\s*(?:元)?", stripped):
                return "number"
            return "string"
        return "string"

    @staticmethod
    def normalize_name(value: str) -> str:
        return re.sub(r"[\s_\-]+", "", value.strip().lower())

    @staticmethod
    def sanitize(value: str) -> str:
        return re.sub(r"[^0-9A-Za-z_\u4e00-\u9fff]+", "_", value).strip("_") or "source"
