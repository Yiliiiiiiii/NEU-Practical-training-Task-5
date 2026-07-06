import json
from collections import defaultdict

from sqlalchemy.orm import Session

from app.db.models import KnowledgePackRecord
from app.schemas.review_workbench import (
    KnowledgeConflictItem,
    KnowledgeConflictResponse,
    KnowledgePackDiffResponse,
    KnowledgePackImpactResponse,
    KnowledgePackRollbackResponse,
)
from app.services.review_knowledge_workflow_service import (
    ReviewKnowledgeWorkflowService,
)
from app.services.review_workbench_service import ReviewWorkbenchService
from app.services.storage_service import StorageService


class KnowledgePackGovernanceService:
    def __init__(self, db: Session, storage: StorageService) -> None:
        self.db = db
        self.storage = storage
        self.workflow = ReviewKnowledgeWorkflowService(db)
        self.workbench = ReviewWorkbenchService(db, storage)

    def conflicts(self) -> KnowledgeConflictResponse:
        active = self.workflow.list_packs("active")
        alias_targets: dict[str, set[str]] = defaultdict(set)
        alias_packs: dict[str, set[str]] = defaultdict(set)
        for pack in active:
            for alias, target in self._pack_alias_pairs(pack.pack_id):
                alias_targets[alias].add(target)
                alias_packs[alias].add(pack.pack_id)
        items = [
            KnowledgeConflictItem(
                conflict_type="active_pack_target_conflict",
                source_label=alias,
                targets=sorted(targets),
                pack_ids=sorted(alias_packs[alias]),
            )
            for alias, targets in sorted(alias_targets.items())
            if len(targets) > 1
        ]
        active_pairs = {
            (alias, target, pack.pack_id)
            for pack in active
            for alias, target in self._pack_alias_pairs(pack.pack_id)
        }
        negative_pairs = {
            (rule.source_label, rule.forbidden_target)
            for rule in self.workbench.list_negative_rules()
        }
        items.extend(
            KnowledgeConflictItem(
                conflict_type="negative_knowledge_conflict",
                source_label=alias,
                targets=[target],
                pack_ids=[pack_id],
            )
            for alias, target, pack_id in sorted(active_pairs)
            if (alias, target) in negative_pairs
        )
        return KnowledgeConflictResponse(total=len(items), items=items)

    def diff(self, pack_id: str) -> KnowledgePackDiffResponse:
        pack = self._pack(pack_id)
        current_pairs = self._pack_alias_pairs(pack_id)
        active_pairs = {
            (alias, target)
            for active_pack in self.workflow.list_packs("active")
            if active_pack.pack_id != pack_id
            and active_pack.schema_id == pack.schema_id
            and active_pack.template_id == pack.template_id
            for alias, target in self._pack_alias_pairs(active_pack.pack_id)
        }
        added: dict[str, list[str]] = defaultdict(list)
        conflicts: list[KnowledgeConflictItem] = []
        active_by_alias: dict[str, set[str]] = defaultdict(set)
        for alias, target in active_pairs:
            active_by_alias[alias].add(target)
        for alias, target in current_pairs:
            if (alias, target) not in active_pairs:
                added[target].append(alias)
            other_targets = active_by_alias.get(alias, set()) - {target}
            if other_targets:
                conflicts.append(
                    KnowledgeConflictItem(
                        conflict_type="active_pack_target_conflict",
                        source_label=alias,
                        targets=sorted({target, *other_targets}),
                        pack_ids=[pack_id],
                    )
                )
        return KnowledgePackDiffResponse(
            pack_id=pack_id,
            added_aliases={
                target: sorted(aliases)
                for target, aliases in sorted(added.items())
            },
            conflicting_aliases=conflicts,
        )

    def impact(self, pack_id: str) -> KnowledgePackImpactResponse:
        self._pack(pack_id)
        items = self.workflow.pack_items(pack_id)
        return KnowledgePackImpactResponse(
            pack_id=pack_id,
            future_rule_count=len(items),
            candidate_ids=[
                item.candidate_id for item in items if item.candidate_id
            ],
            old_snapshot_unchanged=True,
        )

    def assert_can_activate(self, pack_id: str) -> None:
        pack = self._pack(pack_id)
        negative_pairs = {
            (rule.source_label, rule.forbidden_target)
            for rule in self.workbench.list_negative_rules()
        }
        pairs = set(self._pack_alias_pairs(pack_id))
        if pairs & negative_pairs:
            raise ValueError("pack conflicts with negative knowledge")
        active_by_alias: dict[str, set[str]] = defaultdict(set)
        for active in self.workflow.list_packs("active"):
            if active.pack_id == pack_id:
                continue
            for alias, target in self._pack_alias_pairs(active.pack_id):
                active_by_alias[alias].add(target)
        if any(active_by_alias.get(alias, set()) - {target} for alias, target in pairs):
            raise ValueError("pack conflicts with active knowledge pack")
        if pack.status == "archived":
            raise ValueError("archived pack cannot be activated")

    def rollback(self, pack_id: str) -> KnowledgePackRollbackResponse:
        pack = self.workflow.archive_pack(pack_id)
        return KnowledgePackRollbackResponse(
            pack_id=pack.pack_id,
            status=pack.status,
            future_tasks_use_pack=False,
            old_snapshot_unchanged=True,
        )

    def _pack(self, pack_id: str) -> KnowledgePackRecord:
        pack = self.db.get(KnowledgePackRecord, pack_id)
        if pack is None:
            raise LookupError("knowledge pack not found")
        return pack

    def _pack_alias_pairs(self, pack_id: str) -> list[tuple[str, str]]:
        pairs: list[tuple[str, str]] = []
        for item in self.workflow.pack_items(pack_id):
            if item.item_type != "alias":
                continue
            try:
                value = json.loads(item.value_json)
            except json.JSONDecodeError:
                continue
            alias = value.get("alias")
            if isinstance(alias, str):
                pairs.append((alias, item.target_field_id))
        return pairs
