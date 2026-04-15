"""Exception handlers for FastAPI application.

These handlers convert domain exceptions to proper HTTP responses.
"""

import logging

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request | WebSocket, exc: AppException) -> JSONResponse:
    """Handle application exceptions.

    Logs 5xx errors as errors and 4xx as warnings.
    Returns a standardized JSON error response.

    Note: For WebSocket connections, this handler may not be able to return
    a response if the connection was already closed.
    """
    # WebSocket objects don't have a method attribute
    method = getattr(request, "method", "WEBSOCKET")

    log_extra = {
        "error_code": exc.code,
        "status_code": exc.status_code,
        "details": exc.details,
        "path": request.url.path,
        "method": method,
    }

    if exc.status_code >= 500:
        logger.error(f"{exc.code}: {exc.message}", extra=log_extra)
    else:
        logger.warning(f"{exc.code}: {exc.message}", extra=log_extra)

    headers: dict[str, str] = {}
    if exc.status_code == 401:
        headers["WWW-Authenticate"] = "Bearer"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details or None,
            }
        },
        headers=headers,
    )


async def unhandled_exception_handler(request: Request | WebSocket, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions.

    Logs the full exception but returns a generic error to the client
    to avoid leaking sensitive information.
    """
    method = getattr(request, "method", "WEBSOCKET")

    logger.exception(
        "Unhandled exception",
        extra={
            "path": request.url.path,
            "method": method,
        },
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": None,
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI app.

    Call this after creating the FastAPI application instance.
    """
    app.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]
    # Uncomment to catch all unhandled exceptions:
    # app.add_exception_handler(Exception, unhandled_exception_handler)
