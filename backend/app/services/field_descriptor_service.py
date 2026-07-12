from __future__ import annotations

import re
from typing import Any

from app.schemas.field_descriptors import (
    CandidateFieldDescriptor,
    TargetFieldDescriptor,
)
from app.schemas.mapping import FieldCandidate
from app.schemas.mapping_template import MappingTemplate
from app.schemas.target_schema import TargetField
from app.schemas.uir import UIRDocument


class FieldDescriptorService:
    def target_descriptor(
        self, field: TargetField, template: MappingTemplate
    ) -> TargetFieldDescriptor:
        constraints = dict(field.constraints)
        enum_values = constraints.pop("enum", [])
        return TargetFieldDescriptor(
            field_id=field.field_id,
            name=field.name,
            display_name=field.display_name,
            aliases=sorted(
                {
                    *field.aliases,
                    *template.aliases.get(field.field_id, []),
                }
            ),
            description=field.description,
            type=field.type,
            required=field.required,
            enum_values=list(enum_values) if isinstance(enum_values, list) else [],
            format_constraints=constraints,
            parent_path=field.parent_path,
        )

    def candidate_descriptor(
        self, candidate: FieldCandidate, uir: UIRDocument | None = None
    ) -> CandidateFieldDescriptor:
        block = None
        neighbors: list[str] = []
        if uir is not None:
            match = re.match(r"^\$\.blocks\.([^.]+)", candidate.source_path)
            if match:
                block_id = match.group(1)
                for index, item in enumerate(uir.blocks):
                    if item.block_id != block_id:
                        continue
                    block = item
                    for neighbor in uir.blocks[max(0, index - 1) : index + 2]:
                        if neighbor.block_id == block_id or not neighbor.text:
                            continue
                        label = re.split(r"[:：|]", neighbor.text, maxsplit=1)[0].strip()
                        if label:
                            neighbors.append(label)
                    break
        title_path: list[str] = []
        if block is not None:
            raw_path = block.attributes.get("title_path", [])
            if isinstance(raw_path, str):
                title_path = [raw_path]
            elif isinstance(raw_path, list):
                title_path = [str(item) for item in raw_path if str(item).strip()]
        return CandidateFieldDescriptor(
            source_name=candidate.source_name,
            display_name=candidate.display_name,
            source_path=candidate.source_path,
            inferred_type=candidate.inferred_type,
            value_shape=self._value_shape(candidate.value_sample),
            section_title_path=title_path,
            block_type=block.type if block is not None else None,
            neighbor_labels=neighbors,
            source_evidence_type=candidate.evidence_type,
            source_metadata={
                "has_source_blocks": bool(candidate.source_blocks),
                "candidate_confidence": candidate.confidence,
            },
        )

    @staticmethod
    def _value_shape(value: Any) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int | float):
            return "number"
        if isinstance(value, list):
            return "array"
        if isinstance(value, dict):
            return "object"
        if isinstance(value, str):
            if re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", value):
                return "date_like"
            if re.search(r"\d", value):
                return "alphanumeric_text"
            return "text"
        return type(value).__name__
