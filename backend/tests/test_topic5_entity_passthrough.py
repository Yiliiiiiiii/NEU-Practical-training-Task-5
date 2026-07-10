from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.canonical import CanonicalBlock, CanonicalField, CanonicalModel
from app.schemas.content_organization import ContentOrganizationOptions
from app.schemas.reports import MappingReport
from app.schemas.target_schema import TargetSchema
from app.schemas.uir import UIRDocument
from app.services.chunk_organizer_service import ChunkOrganizerService


def _schema() -> TargetSchema:
    return TargetSchema.model_validate(
        {
            "schema_id": "entity_doc",
            "name": "Entity Doc",
            "version": "1.0.0",
            "fields": [
                {
                    "field_id": "issuer",
                    "name": "issuer",
                    "display_name": "Issuer",
                    "type": "string",
                    "required": False,
                }
            ],
        }
    )


def _mapping() -> MappingReport:
    return MappingReport(
        task_id="task-entity",
        schema_id="entity_doc",
        summary={},
        mappings=[],
        unmapped=[],
        review_required_items=[],
    )


def _canonical(entities: list[dict] | None = None) -> CanonicalModel:
    return CanonicalModel(
        canonical_version="1.0",
        task_id="task-entity",
        doc_id="doc-entity",
        schema_id="entity_doc",
        doc_meta={
            "entities": entities or [],
            "metadata": {"issuer": "Guessed Corp"},
            "document_metadata": {"department": "Guessed Department"},
        },
        fields={
            "issuer": CanonicalField(
                value="Guessed Corp",
                type="string",
                source_blocks=["b1"],
            )
        },
        blocks=[
            CanonicalBlock(
                block_id="b1",
                type="paragraph",
                text="OpenAI published the notice.",
                source_blocks=["b1"],
            ),
            CanonicalBlock(
                block_id="b2",
                type="paragraph",
                text="The university acknowledged OpenAI.",
                source_blocks=["b2"],
            ),
            CanonicalBlock(
                block_id="b3",
                type="paragraph",
                text="A separate paragraph.",
                source_blocks=["b3"],
            ),
        ],
    )


def _organize(entities: list[dict] | None = None):
    return ChunkOrganizerService().organize_chunks(
        chunks=[
            {"chunk_id": "c1", "text": "OpenAI published the notice.", "source_block_ids": ["b1"]},
            {
                "chunk_id": "c2",
                "text": "The university acknowledged OpenAI.",
                "source_block_ids": ["b2"],
            },
            {"chunk_id": "c3", "text": "A separate paragraph.", "source_block_ids": ["b3"]},
        ],
        canonical_model=_canonical(entities),
        schema=_schema(),
        mapping_report=_mapping(),
        validation_report=None,
        task_id="task-entity",
        doc_id="doc-entity",
        schema_id="entity_doc",
        template_id="entity-v1",
        options=ContentOrganizationOptions(
            chunk_strategy="source_block_aware",
            target_tokens=128,
            min_tokens=1,
            max_tokens=256,
            overlap_tokens=0,
        ),
    )


def test_linked_entity_is_copied_with_same_upstream_id() -> None:
    chunks, _report = _organize(
        [
            {
                "mention": "OpenAI",
                "canonical_name": "OpenAI",
                "entity_type": "organization",
                "normalized_id": "org:openai",
                "link_status": "linked",
                "confidence": 0.99,
                "source_block_ids": ["b1"],
                "source_agent": "topic7",
            }
        ]
    )

    assert chunks[0]["entity_tags"] == [
        {
            "text": "OpenAI",
            "mention": "OpenAI",
            "canonical_name": "OpenAI",
            "entity_type": "organization",
            "normalized_id": "org:openai",
            "link_status": "linked",
            "source": "upstream",
            "confidence": 0.99,
            "source_block_ids": ["b1"],
            "source_agent": "topic7",
        }
    ]
    assert chunks[1]["entity_tags"] == []
    assert chunks[2]["entity_tags"] == []


@pytest.mark.parametrize("link_status", ["unlinked", "nil"])
def test_unlinked_and_nil_entities_keep_status_without_invented_id(
    link_status: str,
) -> None:
    chunks, _report = _organize(
        [
            {
                "mention": "OpenAI",
                "canonical_name": None,
                "entity_type": "organization",
                "normalized_id": None,
                "link_status": link_status,
                "confidence": None,
                "source_block_ids": ["b1"],
                "source_agent": "topic7",
            }
        ]
    )

    entity = chunks[0]["entity_tags"][0]
    assert entity["link_status"] == link_status
    assert entity["normalized_id"] is None


def test_entity_with_multiple_source_blocks_appears_in_each_relevant_chunk() -> None:
    chunks, _report = _organize(
        [
            {
                "mention": "OpenAI",
                "entity_type": "organization",
                "normalized_id": "org:openai",
                "link_status": "linked",
                "source_block_ids": ["b1", "b2"],
            }
        ]
    )

    assert [len(chunk["entity_tags"]) for chunk in chunks] == [1, 1, 0]


def test_entity_without_block_ids_uses_exact_mention_fallback() -> None:
    chunks, _report = _organize(
        [
            {
                "mention": "OpenAI",
                "entity_type": "organization",
                "normalized_id": None,
                "link_status": "unlinked",
                "source_block_ids": [],
            }
        ]
    )

    assert [len(chunk["entity_tags"]) for chunk in chunks] == [1, 1, 0]


def test_legacy_field_name_entity_inference_is_disabled_by_default() -> None:
    chunks, _report = _organize([])

    assert all(chunk["entity_tags"] == [] for chunk in chunks)


def test_uir_rejects_entity_source_block_that_does_not_exist() -> None:
    with pytest.raises(ValidationError):
        UIRDocument.model_validate(
            {
                "uir_version": "1.0",
                "doc_id": "doc-1",
                "blocks": [{"block_id": "b1", "type": "paragraph", "text": "x"}],
                "entities": [
                    {
                        "mention": "OpenAI",
                        "link_status": "unlinked",
                        "source_block_ids": ["unknown"],
                    }
                ],
            }
        )


def test_legacy_uir_without_entities_still_converts_contract() -> None:
    uir = UIRDocument.model_validate(
        {"uir_version": "1.0", "doc_id": "doc-1", "blocks": []}
    )

    assert uir.entities == []


def test_entity_passthrough_is_deterministic() -> None:
    entities = [
        {
            "mention": "OpenAI",
            "entity_type": "organization",
            "normalized_id": "org:openai",
            "link_status": "linked",
            "source_block_ids": ["b1"],
        }
    ]

    first = _organize(entities)
    second = _organize(entities)

    assert first == second
