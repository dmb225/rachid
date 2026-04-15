"""RAG document service (PostgreSQL async).

Contains business logic for tracking RAG document ingestion, status updates,
file downloads, and cascading deletions across DB, vector store, and file storage.
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.rag_document import RAGDocument

logger = logging.getLogger(__name__)


class RAGDocumentService:
    """Service for RAG document tracking and lifecycle management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_documents(
        self,
        collection_name: str | None = None,
    ) -> list[RAGDocument]:
        """List tracked RAG documents, optionally filtered by collection."""
        query = select(RAGDocument)
        if collection_name:
            query = query.where(RAGDocument.collection_name == collection_name)
        query = query.order_by(RAGDocument.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_document(self, doc_id: str) -> RAGDocument:
        """Get a RAG document by ID.

        Raises:
            NotFoundError: If document does not exist.
        """
        doc = await self.db.get(RAGDocument, UUID(doc_id))
        if not doc:
            raise NotFoundError(
                message="Document not found",
                details={"doc_id": doc_id},
            )
        return doc

    async def create_document(
        self,
        *,
        collection_name: str,
        filename: str,
        filesize: int,
        filetype: str,
        storage_path: str | None = None,
    ) -> RAGDocument:
        """Create a new RAG document tracking record."""
        doc = RAGDocument(
            collection_name=collection_name,
            filename=filename,
            filesize=filesize,
            filetype=filetype,
            storage_path=storage_path,
            status="processing",
        )
        self.db.add(doc)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def complete_ingestion(
        self,
        doc_id: str,
        vector_document_id: str,
        chunk_count: int = 0,
    ) -> None:
        """Mark a document as successfully ingested."""
        doc = await self.get_document(doc_id)
        doc.status = "done"
        doc.vector_document_id = vector_document_id
        doc.chunk_count = chunk_count
        doc.completed_at = datetime.now(UTC)
        await self.db.commit()

    async def fail_ingestion(self, doc_id: str, error_message: str) -> None:
        """Mark a document ingestion as failed."""
        doc = await self.get_document(doc_id)
        doc.status = "error"
        doc.error_message = error_message
        doc.completed_at = datetime.now(UTC)
        await self.db.commit()

    async def retry_ingestion(self, doc_id: str) -> RAGDocument:
        """Reset a failed document for re-ingestion.

        Raises:
            NotFoundError: If document does not exist.
            ValueError: If document status is not 'error'.
        """
        doc = await self.get_document(doc_id)
        if doc.status != "error":
            raise ValueError("Only failed documents can be retried")
        doc.status = "processing"
        doc.error_message = None
        doc.completed_at = None
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def delete_document(
        self,
        doc_id: str,
        ingestion_service: Any = None,
    ) -> None:
        """Delete a document with cascading cleanup.

        Removes the record from the database and attempts to clean up
        the vector store entry and stored file. Failures in cleanup
        are logged but do not prevent the DB deletion.
        """
        doc = await self.get_document(doc_id)

        # Cascade: vector store
        if doc.vector_document_id and ingestion_service:
            try:
                await ingestion_service.remove_document(doc.collection_name, doc.vector_document_id)
            except Exception as e:
                logger.warning(f"Failed to delete from vector store: {e}")

        # Cascade: file storage
        if doc.storage_path:
            try:
                from app.services.file_storage import get_file_storage

                storage = get_file_storage()
                await storage.delete(doc.storage_path)
            except Exception as e:
                logger.warning(f"Failed to delete file: {e}")

        # Cascade: DB record
        await self.db.delete(doc)
        await self.db.commit()

    async def delete_by_collection(self, collection_name: str) -> int:
        """Delete all RAG document records for a collection.

        Returns:
            Number of deleted records.
        """
        from sqlalchemy import delete as sql_delete

        result = await self.db.execute(
            sql_delete(RAGDocument).where(RAGDocument.collection_name == collection_name)
        )
        await self.db.commit()
        return result.rowcount  # type: ignore[no-any-return, attr-defined]

    async def get_download_info(self, doc_id: str) -> tuple[str, str, str]:
        """Get file download information for a document.

        Returns:
            Tuple of (file_path, filename, mime_type).

        Raises:
            NotFoundError: If document or its file does not exist.
        """
        doc = await self.get_document(doc_id)
        if not doc.storage_path:
            raise NotFoundError(message="No file stored for this document")

        from app.services.file_storage import get_file_storage

        storage = get_file_storage()
        file_path = storage.get_full_path(doc.storage_path)
        if not file_path:
            raise NotFoundError(message="File not found on disk")

        mime_map = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "txt": "text/plain",
            "md": "text/markdown",
        }
        mime_type = mime_map.get(doc.filetype, "application/octet-stream")
        return str(file_path), doc.filename, mime_type
