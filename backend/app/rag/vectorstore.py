import logging
from abc import ABC, abstractmethod
from typing import Any

from app.rag.models import CollectionInfo, Document, DocumentInfo, DocumentPageChunk, SearchResult

logger = logging.getLogger(__name__)


class BaseVectorStore(ABC):
    """Abstract base class for vector store implementations."""

    @abstractmethod
    async def insert_document(self, collection_name: str, document: Document) -> None:
        """Embeds and stores document chunks."""

    @abstractmethod
    async def search(
        self, collection_name: str, query: str, limit: int = 4, filter: str = ""
    ) -> list[SearchResult]:
        """Retrieves similar chunks based on a text query."""

    @abstractmethod
    async def delete_collection(self, collection_name: str) -> None:
        """Removes a collection and all its data."""

    @abstractmethod
    async def delete_document(self, collection_name: str, document_id: str) -> None:
        """Removes all chunks associated with a document ID."""

    @abstractmethod
    async def get_collection_info(self, collection_name: str) -> CollectionInfo:
        """Returns metadata and stats about a collection."""

    @abstractmethod
    async def list_collections(self) -> list[str]:
        """Returns list of all collection names."""

    @abstractmethod
    async def get_documents(self, collection_name: str) -> list[DocumentInfo]:
        """Returns list of unique documents in a collection."""

    def _build_chunk_metadata(
        self, chunk: "DocumentPageChunk", document: Document
    ) -> dict[str, Any]:
        """Build metadata dict for a chunk."""
        meta = {
            "page_num": chunk.page_num,
            "chunk_num": chunk.chunk_num,
            "has_images": bool(getattr(chunk, "images", None)),
            "image_count": len(getattr(chunk, "images", [])),
            **document.metadata.model_dump(),
        }
        return meta

    def _sanitize_id(self, document_id: str) -> str:
        """Sanitize document_id to prevent filter injection."""
        return document_id.replace('"', "").replace("\\", "")

    def _group_documents(self, results: list[dict[str, Any]]) -> list[DocumentInfo]:
        """Group query results by parent_doc_id into DocumentInfo list."""
        doc_map: dict[str, dict[str, Any]] = {}
        for item in results:
            doc_id = item.get("parent_doc_id")
            metadata = item.get("metadata", {})
            if doc_id and doc_id not in doc_map:
                doc_map[doc_id] = {
                    "document_id": doc_id,
                    "filename": metadata.get("filename"),
                    "filesize": metadata.get("filesize"),
                    "filetype": metadata.get("filetype"),
                    "additional_info": {
                        "source_path": metadata.get("source_path", ""),
                        "content_hash": metadata.get("content_hash", ""),
                        **(metadata.get("additional_info") or {}),
                    },
                    "chunk_count": 0,
                }
            if doc_id:
                doc_map[doc_id]["chunk_count"] += 1
        return [
            DocumentInfo(
                document_id=d["document_id"],
                filename=d.get("filename"),
                filesize=d.get("filesize"),
                filetype=d.get("filetype"),
                chunk_count=d["chunk_count"],
                additional_info=d.get("additional_info"),
            )
            for d in doc_map.values()
        ]


import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings as app_settings
from app.rag.config import RAGSettings
from app.rag.embeddings import EmbeddingService


def _validate_collection_name(name: str) -> str:
    """Validate collection name to prevent SQL injection."""
    import re

    if not re.match(r"^[a-zA-Z0-9_]+$", name):
        raise ValueError(
            f"Invalid collection name: {name}. Only alphanumeric and underscores allowed."
        )
    return name


class PgVectorStore(BaseVectorStore):
    """PostgreSQL + pgvector implementation.

    Uses the existing PostgreSQL database with pgvector extension.
    No additional Docker services needed.
    """

    def __init__(self, settings: RAGSettings, embedding_service: EmbeddingService):
        self.settings = settings
        self.embedder = embedding_service
        self.dim = settings.embeddings_config.dim
        self.engine = create_async_engine(app_settings.DATABASE_URL, echo=False)
        self.async_session = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    def _table(self, name: str) -> str:
        """Get validated table name for a collection."""
        return f"rag_{_validate_collection_name(name)}"

    async def _ensure_collection(self, name: str) -> None:
        """Create table for collection if not exists."""
        table = self._table(name)
        async with self.async_session() as session:
            await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await session.execute(
                text(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id VARCHAR(100) PRIMARY KEY,
                    parent_doc_id VARCHAR(100),
                    content TEXT,
                    embedding vector({self.dim}),
                    metadata JSONB DEFAULT '{{}}'::jsonb
                )
            """)
            )
            await session.execute(
                text(f"""
                CREATE INDEX IF NOT EXISTS {table}_embedding_idx
                ON {table} USING hnsw (embedding vector_cosine_ops)
            """)
            )
            await session.commit()

    async def insert_document(self, collection_name: str, document: Document) -> None:
        table = self._table(collection_name)
        await self._ensure_collection(collection_name)
        if not document.chunked_pages:
            raise ValueError("Document has no chunked pages.")
        vectors = self.embedder.embed_document(document)
        async with self.async_session() as session:
            for i, chunk in enumerate(document.chunked_pages):
                meta = self._build_chunk_metadata(chunk, document)
                await session.execute(
                    text(f"""
                        INSERT INTO {table} (id, parent_doc_id, content, embedding, metadata)
                        VALUES (:id, :parent_doc_id, :content, :embedding, :metadata)
                        ON CONFLICT (id) DO UPDATE SET content = :content, embedding = :embedding, metadata = :metadata
                    """),
                    {
                        "id": chunk.chunk_id,
                        "parent_doc_id": chunk.parent_doc_id,
                        "content": chunk.chunk_content,
                        "embedding": str(vectors[i]),
                        "metadata": json.dumps(meta),
                    },
                )
            await session.commit()

    async def search(
        self, collection_name: str, query: str, limit: int = 4, filter: str = ""
    ) -> list[SearchResult]:
        table = self._table(collection_name)
        query_vector = self.embedder.embed_query(query)
        async with self.async_session() as session:
            result = await session.execute(
                text(f"""
                    SELECT content, parent_doc_id, metadata,
                           1 - (embedding <=> :query_vec) AS score
                    FROM {table}
                    ORDER BY embedding <=> :query_vec
                    LIMIT :limit
                """),
                {"query_vec": str(query_vector), "limit": limit},
            )
            rows = result.fetchall()
        return [
            SearchResult(
                content=row[0],
                score=float(row[3]),
                metadata=row[2] if isinstance(row[2], dict) else json.loads(row[2]),
                parent_doc_id=row[1],
            )
            for row in rows
        ]

    async def get_collection_info(self, collection_name: str) -> CollectionInfo:
        table = self._table(collection_name)
        async with self.async_session() as session:
            result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar() or 0
        return CollectionInfo(name=collection_name, total_vectors=count, dim=self.dim)

    async def delete_collection(self, collection_name: str) -> None:
        table = self._table(collection_name)
        async with self.async_session() as session:
            await session.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await session.commit()

    async def delete_document(self, collection_name: str, document_id: str) -> None:
        table = self._table(collection_name)
        sanitized = self._sanitize_id(document_id)
        async with self.async_session() as session:
            await session.execute(
                text(f"DELETE FROM {table} WHERE parent_doc_id = :doc_id"),
                {"doc_id": sanitized},
            )
            await session.commit()

    async def get_documents(self, collection_name: str) -> list[DocumentInfo]:
        table = self._table(collection_name)
        await self._ensure_collection(collection_name)
        async with self.async_session() as session:
            result = await session.execute(text(f"SELECT parent_doc_id, metadata FROM {table}"))
            rows = result.fetchall()
        results = [
            {
                "parent_doc_id": row[0],
                "metadata": row[1] if isinstance(row[1], dict) else json.loads(row[1]),
            }
            for row in rows
        ]
        return self._group_documents(results)

    async def list_collections(self) -> list[str]:
        async with self.async_session() as session:
            result = await session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'rag_%' AND table_schema = 'public'"
                )
            )
            return [row[0].replace("rag_", "") for row in result.fetchall()]
