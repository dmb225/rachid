"""RAG sync service (PostgreSQL async).

Contains business logic for managing RAG synchronization operations
and their associated log entries.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.sync_log import SyncLog


class RAGSyncService:
    """Service for RAG sync operation management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_sync_logs(
        self,
        collection_name: str | None = None,
        limit: int = 20,
    ) -> list[SyncLog]:
        """List sync operation logs, optionally filtered by collection."""
        query = select(SyncLog)
        if collection_name:
            query = query.where(SyncLog.collection_name == collection_name)
        query = query.order_by(SyncLog.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_sync_log(self, sync_id: str) -> SyncLog:
        """Get a sync log by ID.

        Raises:
            NotFoundError: If sync log does not exist.
        """
        log = await self.db.get(SyncLog, UUID(sync_id))
        if not log:
            raise NotFoundError(
                message="Sync log not found",
                details={"sync_id": sync_id},
            )
        return log

    async def create_sync_log(
        self,
        *,
        source: str,
        collection_name: str,
        mode: str,
    ) -> SyncLog:
        """Create a new sync log entry."""
        log = SyncLog(
            source=source,
            collection_name=collection_name,
            status="running",
            mode=mode,
        )
        self.db.add(log)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def complete_sync(
        self,
        sync_id: str,
        *,
        status: str,
        total_files: int = 0,
        ingested: int = 0,
        updated: int = 0,
        skipped: int = 0,
        failed: int = 0,
        error_message: str | None = None,
    ) -> None:
        """Mark a sync operation as completed (done or error)."""
        log = await self.get_sync_log(sync_id)
        log.status = status
        log.total_files = total_files
        log.ingested = ingested
        log.updated = updated
        log.skipped = skipped
        log.failed = failed
        log.error_message = error_message
        log.completed_at = datetime.now(UTC)
        await self.db.commit()

    async def cancel_sync(self, sync_id: str) -> SyncLog:
        """Cancel a running sync operation.

        Raises:
            NotFoundError: If sync log does not exist.
            ValueError: If sync is not in 'running' state.
        """
        log = await self.get_sync_log(sync_id)
        if log.status != "running":
            raise ValueError("Sync is not running")
        log.status = "cancelled"
        log.completed_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(log)
        return log
