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
    }
    TITLE_CANDIDATE_NAMES = (
        "document_title",
        "policy_title",
        "meeting_title",
        "guide_title",
    )
    HEADED_LIST_NAMES = {
        "申请材料",
        "办理材料",
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
    FULL_DATE_PATTERN = (
        r"(?:\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日"
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
        rf"(?P<label>创建日期|形成日期|发布日期|公开日期|发文日期|印发日期|成文日期|"
        rf"会议日期|会议时间|召开日期|召开时间)\s*[:：]\s*"
        rf"(?P<value>{FULL_DATE_PATTERN})"
    )
    PHONE_PATTERN = re.compile(
        r"(?:联系电话|咨询电话|联系方式|电话)\s*[:：]\s*"
        r"(?P<value>(?:\+?86[-\s]?)?"
        r"(?:1[3-9]\d{9}|0\d{2,3}[-\s]?\d{7,8})(?:[-转]\d{1,6})?)"
    )
    ISSUER_PATTERN = re.compile(
        r"(?:发文机关|发布机关|制定机关|印发机关|主办单位|发布单位)"
        r"\s*[:：]\s*(?P<value>[^，。；;\n]{2,100})"
    )
    POLICY_ORGANIZATION_PATTERN = re.compile(
        r"[\u4e00-\u9fff]{2,30}?"
        r"(?:国家互联网信息办公室|办公厅|办公室|委员会|监管总局|总局|改革委|"
        r"人民银行|管理局|部|署|厅|委|局)"
    )
    POLICY_URL_PUBLISH_DATE_PATTERN = re.compile(r"/t(?P<date>20\d{6})(?:_|[/.])")
    POLICY_URL_DATE_HOSTS = {"moe.gov.cn", "www.moe.gov.cn"}
    POLICY_PAGE_BANNER_PATTERN = re.compile(
        r"中国政府网\s*(?P<date>20\d{2})-(?P<month>\d{1,2})-(?P<day>\d{1,2})"
    )
    POLICY_ISSUER_SOURCE_NAMES = {
        "issuer",
        "发文机关",
        "发布单位",
        "颁布机构",
        "制定机关",
        "印发机关",
    }
    POLICY_PUBLISH_DATE_SOURCE_NAMES = {
        "publishdate",
        "发布日期",
        "发文日期",
        "印发日期",
        "发布时间",
        "公开日期",
    }
    FULL_DATE_REGEX = re.compile(FULL_DATE_PATTERN)

    def extract_candidates(self, task_id: str, uir: UIRDocument) -> list[FieldCandidate]:
        candidates: list[FieldCandidate] = []
        seen_names: dict[str, int] = {}

        for key, value in uir.metadata.items():
            if key in self.CONTROL_METADATA_KEYS:
                continue
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

        if uir.metadata.get("domain") == "meeting_doc":
            meeting_date = self._meeting_date_candidate(task_id, uir, seen_names)
            if meeting_date is not None:
                candidates.append(meeting_date)
            candidates.extend(self._meeting_opening_candidates(task_id, uir, seen_names))
        elif uir.metadata.get("domain") == "policy_doc":
            candidates.extend(
                self._policy_document_candidates(task_id, uir, seen_names, candidates)
            )

        self._add_traceable_block_candidates(task_id, uir, candidates, seen_names)
        return candidates

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
                    )

            for source_name, display_name, value, confidence in self._paragraph_regex_values(
                text
            ):
                append_candidate(
                    source_path=f"$.blocks.{block.block_id}.text",
                    source_name=source_name,
                    value=value,
                    source_blocks=[block.block_id],
                    source_kind="paragraph_regex",
                    confidence=confidence,
                    display_name=display_name,
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
    ) -> list[tuple[str, str, str, float]]:
        values: list[tuple[str, str, str, float]] = []
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
                values.append(
                    (source_name, display_name, match.group("value"), confidence)
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
                )
            )
        for match in self._bounded_matches(self.FULL_DATE_REGEX, text):
            values.append(("paragraph_regex.date", "date", match.group(0), 0.55))
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
            re.compile(r"[二〇○零一二三四五六七八九十]{4}\s*年\s*[一二三四五六七八九十]{1,3}\s*月\s*[一二三四五六七八九十]{1,3}\s*日"),
            re.compile(r"\d{1,2}\s*月\s*\d{1,2}\s*日"),
        ]
        matches: list[tuple[int, int, str, str]] = []
        for index, block in enumerate(uir.blocks):
            text = block.text or ""
            if not text or "生成日期" in text:
                continue
            for pattern in patterns:
                match = pattern.search(text)
                if match is None:
                    continue
                score = 3 if "主持召开" in text else 2 if "日期" in text else 1
                matches.append((score, -index, match.group(0), block.block_id))
                break
        if not matches:
            return None
        _score, _index, value, block_id = max(matches)
        value = re.sub(r"\s+", "", value)
        return self._candidate(
            task_id=task_id,
            uir=uir,
            source_path=f"$.blocks.{block_id}.text",
            source_name="meeting date",
            value=value,
            source_blocks=[block_id],
            source_kind="derived_meeting_date",
            seen_names=seen_names,
        )

    def _meeting_opening_candidates(
        self,
        task_id: str,
        uir: UIRDocument,
        seen_names: dict[str, int],
    ) -> list[FieldCandidate]:
        candidates: list[FieldCandidate] = []
        number_pattern = re.compile(r"第\s*(\d+)\s*次(?:常务|专题|全体)?会议")
        chair_pattern = re.compile(
            r"(?:县委副书记、代县长|区政府党组书记、区长|市委副书记、市长|"
            r"县委副书记、县长|县长|区长|市长)?"
            r"(?P<name>[\u4e00-\u9fff·]{2,4})\s*主持召开"
        )
        for block in uir.blocks:
            text = block.text if isinstance(block.text, str) else ""
            if not text:
                continue
            number_match = number_pattern.search(text)
            if number_match is not None and not any(
                item.source_name == "meeting_number" for item in candidates
            ):
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text",
                        source_name="meeting_number",
                        value=f"第{number_match.group(1)}次",
                        source_blocks=[block.block_id],
                        source_kind="meeting_opening",
                        seen_names=seen_names,
                        confidence=0.9,
                    )
                )
            chair_match = chair_pattern.search(text)
            if chair_match is not None and not any(
                item.source_name == "chairperson" for item in candidates
            ):
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text",
                        source_name="chairperson",
                        value=chair_match.group("name"),
                        source_blocks=[block.block_id],
                        source_kind="meeting_opening",
                        seen_names=seen_names,
                        confidence=0.9,
                    )
                )
            if candidates and {item.source_name for item in candidates} == {
                "meeting_number",
                "chairperson",
            }:
                break
        return candidates

    def _policy_document_candidates(
        self,
        task_id: str,
        uir: UIRDocument,
        seen_names: dict[str, int],
        existing_candidates: list[FieldCandidate],
    ) -> list[FieldCandidate]:
        candidates: list[FieldCandidate] = []
        blocks = list(uir.blocks)
        existing_names = {
            self.normalize_name(candidate.source_name) for candidate in existing_candidates
        }

        if not existing_names.intersection(self.POLICY_ISSUER_SOURCE_NAMES):
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
                            source_kind="policy_signature",
                            seen_names=seen_names,
                            confidence=0.9,
                        )
                    )
                    break

        source_url = uir.metadata.get("source_url")
        has_publish_date = bool(
            existing_names.intersection(self.POLICY_PUBLISH_DATE_SOURCE_NAMES)
        )
        if (
            not has_publish_date
            and isinstance(source_url, str)
            and urlparse(source_url).hostname in self.POLICY_URL_DATE_HOSTS
        ):
            url_match = self.POLICY_URL_PUBLISH_DATE_PATTERN.search(source_url)
            if url_match is not None:
                raw_date = url_match.group("date")
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path="$.metadata.source_url",
                        source_name="publish_date",
                        value=f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}",
                        source_blocks=[],
                        source_kind="official_page_url",
                        seen_names=seen_names,
                        confidence=0.9,
                    )
                )

        if not has_publish_date and not any(
            item.source_name == "publish_date" for item in candidates
        ):
            for block in blocks:
                text = block.text.strip() if isinstance(block.text, str) else ""
                banner_match = self.POLICY_PAGE_BANNER_PATTERN.fullmatch(text)
                if banner_match is None:
                    continue
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text",
                        source_name="publish_date",
                        value=(
                            f"{banner_match.group('date')}-"
                            f"{int(banner_match.group('month')):02d}-"
                            f"{int(banner_match.group('day')):02d}"
                        ),
                        source_blocks=[block.block_id],
                        source_kind="official_page_banner",
                        seen_names=seen_names,
                        confidence=0.9,
                    )
                )
                break
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
            inferred_type=self.infer_type(value),
            source_blocks=source_blocks,
            confidence=confidence,
            evidence=[f"extracted from {source_kind}"],
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
