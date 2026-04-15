"""File upload and download endpoints for chat attachments."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, FileUploadSvc
from app.schemas.file import FileInfo, FileUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    file_upload_svc: FileUploadSvc = None,  # type: ignore[assignment]
    current_user: CurrentUser = None,  # type: ignore[assignment]
) -> Any:
    """Upload a file for use in chat."""
    data = await file.read()
    is_valid, error = file_upload_svc.validate_upload(file.content_type, len(data))
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    file_type = file_upload_svc.classify_file(file.content_type or "", file.filename or "unknown")
    parsed_content = await file_upload_svc.parse_content(data, file_type, file.content_type or "")

    from app.services.file_storage import get_file_storage

    storage = get_file_storage()
    storage_path = await storage.save(str(current_user.id), file.filename or "unknown", data)
    chat_file = await file_upload_svc.create_chat_file(
        user_id=current_user.id,
        filename=file.filename or "unknown",
        mime_type=file.content_type or "application/octet-stream",
        size=len(data),
        storage_path=storage_path,
        file_type=file_type,
        parsed_content=parsed_content,
    )

    return FileUploadResponse(
        id=chat_file.id,
        filename=chat_file.filename,
        mime_type=chat_file.mime_type,
        size=chat_file.size,
        file_type=chat_file.file_type,
    )


@router.get("/{file_id}")
async def download_file(
    file_id: UUID,
    file_upload_svc: FileUploadSvc = None,  # type: ignore[assignment]
    current_user: CurrentUser = None,  # type: ignore[assignment]
) -> Any:
    """Download a file. Only the owner can access their files."""
    from app.core.exceptions import NotFoundError
    from app.services.file_storage import get_file_storage

    try:
        chat_file = await file_upload_svc.get_user_file(file_id, current_user.id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        ) from None

    storage = get_file_storage()
    file_path = storage.get_full_path(chat_file.storage_path)
    if not file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    return FileResponse(path=file_path, filename=chat_file.filename, media_type=chat_file.mime_type)


@router.get("/{file_id}/info", response_model=FileInfo)
async def get_file_info(
    file_id: UUID,
    file_upload_svc: FileUploadSvc = None,  # type: ignore[assignment]
    current_user: CurrentUser = None,  # type: ignore[assignment]
) -> Any:
    """Get file metadata. Only the owner can access."""
    from app.core.exceptions import NotFoundError

    try:
        chat_file = await file_upload_svc.get_user_file(file_id, current_user.id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        ) from None

    return FileInfo(
        id=chat_file.id,
        filename=chat_file.filename,
        mime_type=chat_file.mime_type,
        size=chat_file.size,
        file_type=chat_file.file_type,
        created_at=chat_file.created_at,
        user_id=chat_file.user_id,
    )
