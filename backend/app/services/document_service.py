from sqlalchemy.orm import Session

from app.db.models import Document
from app.schemas.uir import UIRDocument
from app.services.storage_service import StorageService


class DocumentService:
    def __init__(self, db: Session, storage: StorageService) -> None:
        self.db = db
        self.storage = storage

    def import_uir(self, uir: UIRDocument) -> Document:
        relative_path = f"documents/{uir.doc_id}/uir.json"
        self.storage.save_json(relative_path, uir.model_dump(mode="json"))

        record = self.db.get(Document, uir.doc_id)
        if record is None:
            record = Document(
                doc_id=uir.doc_id,
                title=self._extract_title(uir),
                uir_version=uir.uir_version,
                source_name=uir.source.source_name if uir.source else None,
                storage_path=relative_path,
                block_count=len(uir.blocks),
                metadata_json=uir.model_dump_json(include={"metadata"}),
            )
            self.db.add(record)
        else:
            record.title = self._extract_title(uir)
            record.uir_version = uir.uir_version
            record.source_name = uir.source.source_name if uir.source else None
            record.storage_path = relative_path
            record.block_count = len(uir.blocks)
            record.metadata_json = uir.model_dump_json(include={"metadata"})

        self.db.commit()
        self.db.refresh(record)
        return record

    def list_documents(self, page: int = 1, page_size: int = 20) -> tuple[list[Document], int]:
        query = self.db.query(Document)
        total = query.count()
        items = (
            query.order_by(Document.created_at.desc())
            .offset(max(page - 1, 0) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def get_document(self, doc_id: str) -> Document | None:
        return self.db.get(Document, doc_id)

    def read_uir(self, document: Document) -> dict:
        data = self.storage.read_json(document.storage_path)
        if not isinstance(data, dict):
            raise ValueError("stored UIR must be a JSON object")
        return data

    @staticmethod
    def _extract_title(uir: UIRDocument) -> str | None:
        for key in ("title", "文档标题", "政策名称", "标题"):
            value = uir.metadata.get(key)
            if isinstance(value, str) and value:
                return value
        for block in uir.blocks:
            if block.type == "heading" and block.level == 1 and block.text:
                return block.text
        return None
