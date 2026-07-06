import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import (
    Base,
    KnowledgePackItemRecord,
    KnowledgePackRecord,
)
from app.schemas.review_workbench import NegativeKnowledgeRule
from app.services.knowledge_pack_governance_service import (
    KnowledgePackGovernanceService,
)
from app.services.storage_service import StorageService


def make_service(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'packs.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    storage = StorageService(tmp_path / "storage")
    return session, storage, KnowledgePackGovernanceService(session, storage)


def add_pack(
    session,
    pack_id: str,
    *,
    status: str,
    alias: str,
    target_field: str,
) -> None:
    session.add(
        KnowledgePackRecord(
            pack_id=pack_id,
            name=pack_id,
            schema_id="policy_doc",
            template_id="policy_doc_base_v1",
            version="1.0.0",
            status=status,
            created_by="test",
        )
    )
    session.add(
        KnowledgePackItemRecord(
            item_id=f"{pack_id}_item",
            pack_id=pack_id,
            item_type="alias",
            target_field_id=target_field,
            value_json=json.dumps({"alias": alias}, ensure_ascii=False),
        )
    )
    session.commit()


def test_detects_active_pack_alias_conflict(tmp_path) -> None:
    session, _storage, service = make_service(tmp_path)
    add_pack(session, "pack_a", status="active", alias="发文单位", target_field="issuer")
    add_pack(session, "pack_b", status="active", alias="发文单位", target_field="publisher")

    conflicts = service.conflicts()

    assert conflicts.total == 1
    assert conflicts.items[0].conflict_type == "active_pack_target_conflict"


def test_negative_knowledge_blocks_pack_activation(tmp_path) -> None:
    session, storage, service = make_service(tmp_path)
    add_pack(session, "pack_draft", status="draft", alias="控制价", target_field="award_amount")
    storage.save_json(
        "knowledge/negative_rules.json",
        [
            NegativeKnowledgeRule(
                source_label="控制价",
                forbidden_target="award_amount",
                reason="not award amount",
            ).model_dump(mode="json")
        ],
    )

    with pytest.raises(ValueError, match="negative knowledge"):
        service.assert_can_activate("pack_draft")


def test_rollback_archives_pack_without_rewriting_snapshots(tmp_path) -> None:
    session, _storage, service = make_service(tmp_path)
    add_pack(session, "pack_active", status="active", alias="发文单位", target_field="issuer")

    result = service.rollback("pack_active")

    assert result.status == "archived"
    assert result.future_tasks_use_pack is False
    assert result.old_snapshot_unchanged is True
