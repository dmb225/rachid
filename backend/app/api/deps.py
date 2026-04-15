"""API dependencies.

Dependency injection factories for services, repositories, and authentication.
"""
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals

from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.db.session import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

DBSession = Annotated[AsyncSession, Depends(get_db_session)]
from fastapi import Request

from app.clients.redis import RedisClient


async def get_redis(request: Request) -> RedisClient:
    """Get Redis client from lifespan state."""
    return request.state.redis  # type: ignore[no-any-return]


Redis = Annotated[RedisClient, Depends(get_redis)]


# === Service Dependencies ===

from app.services.user import UserService
from app.services.session import SessionService
from app.services.webhook import WebhookService
from app.services.conversation import ConversationService


def get_user_service(db: DBSession) -> UserService:
    """Create UserService instance with database session."""
    return UserService(db)


def get_session_service(db: DBSession) -> SessionService:
    """Create SessionService instance with database session."""
    return SessionService(db)


UserSvc = Annotated[UserService, Depends(get_user_service)]
SessionSvc = Annotated[SessionService, Depends(get_session_service)]


def get_webhook_service(db: DBSession) -> WebhookService:
    """Create WebhookService instance with database session."""
    return WebhookService(db)


WebhookSvc = Annotated[WebhookService, Depends(get_webhook_service)]


def get_conversation_service(db: DBSession) -> ConversationService:
    """Create ConversationService instance with database session."""
    return ConversationService(db)


ConversationSvc = Annotated[ConversationService, Depends(get_conversation_service)]
from app.services.rag_document import RAGDocumentService
from app.services.rag_sync import RAGSyncService
from app.services.sync_source import SyncSourceService


def get_rag_document_service(db: DBSession) -> RAGDocumentService:
    """Create RAGDocumentService instance with database session."""
    return RAGDocumentService(db)


def get_rag_sync_service(db: DBSession) -> RAGSyncService:
    """Create RAGSyncService instance with database session."""
    return RAGSyncService(db)


def get_sync_source_service(db: DBSession) -> SyncSourceService:
    """Create SyncSourceService instance with database session."""
    return SyncSourceService(db)


RAGDocumentSvc = Annotated[RAGDocumentService, Depends(get_rag_document_service)]
RAGSyncSvc = Annotated[RAGSyncService, Depends(get_rag_sync_service)]
SyncSourceSvc = Annotated[SyncSourceService, Depends(get_sync_source_service)]
from app.services.file_upload import FileUploadService


def get_file_upload_service(db: DBSession) -> FileUploadService:
    """Create FileUploadService instance with database session."""
    return FileUploadService(db)


FileUploadSvc = Annotated[FileUploadService, Depends(get_file_upload_service)]

# === Authentication Dependencies ===

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.db.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_service: UserSvc,
) -> User:
    """Get current authenticated user from JWT token.

    Returns the full User object including role information.

    Raises:
        AuthenticationError: If token is invalid or user not found.
    """
    from uuid import UUID

    from app.core.security import verify_token

    payload = verify_token(token)
    if payload is None:
        raise AuthenticationError(message="Invalid or expired token")

    # Ensure this is an access token, not a refresh token
    if payload.get("type") != "access":
        raise AuthenticationError(message="Invalid token type")

    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError(message="Invalid token payload")

    user = await user_service.get_by_id(UUID(user_id))
    if not user.is_active:
        raise AuthenticationError(message="User account is disabled")

    return user


class RoleChecker:
    """Dependency class for role-based access control.

    Usage:
        # Require admin role
        @router.get("/admin-only")
        async def admin_endpoint(
            user: Annotated[User, Depends(RoleChecker(UserRole.ADMIN))]
        ):
            ...

        # Require any authenticated user
        @router.get("/users")
        async def users_endpoint(
            user: Annotated[User, Depends(get_current_user)]
        ):
            ...
    """

    def __init__(self, required_role: UserRole) -> None:
        self.required_role = required_role

    async def __call__(
        self,
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        """Check if user has the required role.

        Raises:
            AuthorizationError: If user doesn't have the required role.
        """
        if not user.has_role(self.required_role):
            raise AuthorizationError(
                message=f"Role '{self.required_role.value}' required for this action"
            )
        return user


async def get_current_active_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current user and verify they are a superuser.

    Raises:
        AuthorizationError: If user is not a superuser.
    """
    if not current_user.has_role(UserRole.ADMIN):
        raise AuthorizationError(message="Admin privileges required")
    return current_user


# Type aliases for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentSuperuser = Annotated[User, Depends(get_current_active_superuser)]
CurrentAdmin = Annotated[User, Depends(RoleChecker(UserRole.ADMIN))]


# WebSocket authentication dependency
from fastapi import WebSocket, Query, Cookie


async def get_current_user_ws(
    websocket: WebSocket,
    token: str | None = Query(None, alias="token"),
    access_token: str | None = Cookie(None),
) -> User:
    """Get current user from WebSocket JWT token.

    Token can be passed either as:
    - Query parameter: ws://...?token=<jwt>
    - Cookie: access_token cookie (set by HTTP login)

    Raises:
        AuthenticationError: If token is invalid or user not found.
    """
    from uuid import UUID

    from app.core.security import verify_token

    # Try query parameter first, then cookie
    auth_token = token or access_token

    if not auth_token:
        await websocket.close(code=4001, reason="Missing authentication token")
        raise AuthenticationError(message="Missing authentication token")

    payload = verify_token(auth_token)
    if payload is None:
        await websocket.close(code=4001, reason="Invalid or expired token")
        raise AuthenticationError(message="Invalid or expired token")

    if payload.get("type") != "access":
        await websocket.close(code=4001, reason="Invalid token type")
        raise AuthenticationError(message="Invalid token type")

    user_id = payload.get("sub")
    if user_id is None:
        await websocket.close(code=4001, reason="Invalid token payload")
        raise AuthenticationError(message="Invalid token payload")

    from app.db.session import get_db_context

    async with get_db_context() as db:
        user_service = UserService(db)
        user = await user_service.get_by_id(UUID(user_id))

    if not user.is_active:
        await websocket.close(code=4001, reason="User account is disabled")
        raise AuthenticationError(message="User account is disabled")

    return user


import secrets

from fastapi.security import APIKeyHeader


api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)


async def verify_api_key(
    api_key: Annotated[str | None, Depends(api_key_header)],
) -> str:
    """Verify API key from header.

    Uses constant-time comparison to prevent timing attacks.

    Raises:
        AuthenticationError: If API key is missing.
        AuthorizationError: If API key is invalid.
    """
    if api_key is None:
        raise AuthenticationError(message="API Key header missing")
    if not secrets.compare_digest(api_key, settings.API_KEY):
        raise AuthorizationError(message="Invalid API Key")
    return api_key


ValidAPIKey = Annotated[str, Depends(verify_api_key)]

# === RAG Service Dependencies ===

from app.rag.embeddings import EmbeddingService
from app.rag.ingestion import IngestionService
from app.rag.documents import DocumentProcessor
from fastapi import Request
from app.core.config import settings
from app.rag.retrieval import RetrievalService
from app.rag.vectorstore import PgVectorStore


def get_embedding_service(request: Request) -> EmbeddingService:
    """Get embedding service from lifespan state or create new if not available."""
    if request and hasattr(request.state, "embedding_service"):
        return request.state.embedding_service  # type: ignore[no-any-return]
    return EmbeddingService(settings=settings.rag)


# Type Alias for the Embedder
EmbeddingSvc = Annotated[EmbeddingService, Depends(get_embedding_service)]

from app.rag.vectorstore import BaseVectorStore


def get_vectorstore(request: Request, embedder: EmbeddingSvc) -> BaseVectorStore:
    """Get vector store client from lifespan state or create new."""
    if request and hasattr(request.state, "vector_store"):
        return request.state.vector_store  # type: ignore[no-any-return]
    return PgVectorStore(settings=settings.rag, embedding_service=embedder)


VectorStoreSvc = Annotated[BaseVectorStore, Depends(get_vectorstore)]


def get_retrieval_service(vector_store: VectorStoreSvc) -> RetrievalService:
    """Create RetrievalService instance."""
    from app.rag.reranker import RerankService

    rerank_service = RerankService(settings=settings.rag)
    return RetrievalService(
        vector_store=vector_store,
        settings=settings.rag,
        rerank_service=rerank_service,
    )


RetrievalSvc = Annotated[RetrievalService, Depends(get_retrieval_service)]


def get_document_processor() -> DocumentProcessor:
    """Create DocumentProcessor instance."""
    return DocumentProcessor(settings=settings.rag)


DocumentProcessorSvc = Annotated[DocumentProcessor, Depends(get_document_processor)]


def get_ingestion_service(
    processor: DocumentProcessorSvc,
    vector_store: VectorStoreSvc,
    request: Request,
) -> IngestionService:
    """Create IngestionService instance."""

    # Wire webhook dispatch for RAG events
    async def on_rag_event(event: str, data: dict):
        from app.services.webhook import WebhookService

        db = request.state.db if hasattr(request.state, "db") else None
        if db:
            webhook_service = WebhookService(db)
            await webhook_service.dispatch_event(event, data)

    return IngestionService(processor=processor, vector_store=vector_store, on_event=on_rag_event)


IngestionSvc = Annotated[IngestionService, Depends(get_ingestion_service)]
