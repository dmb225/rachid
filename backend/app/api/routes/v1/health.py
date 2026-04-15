"""Health check endpoints.

Provides Kubernetes-compatible health check endpoints:
- /health - Simple liveness check
- /health/live - Detailed liveness probe
- /health/ready - Readiness probe with dependency checks
"""
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.api.deps import DBSession, Redis

router = APIRouter()


def _build_health_response(
    status: str,
    checks: dict[str, Any] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a structured health response."""
    response: dict[str, Any] = {
        "status": status,
        "timestamp": datetime.now(UTC).isoformat(),
        "service": settings.PROJECT_NAME,
    }
    if checks is not None:
        response["checks"] = checks
    if details is not None:
        response["details"] = details
    return response


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Simple liveness probe - check if application is running.

    This is a lightweight check that should always succeed if the
    application is running. Use this for basic connectivity tests.

    Returns:
        {"status": "healthy"}
    """
    return {
        "status": "healthy",
        "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB,
    }


@router.get("/health/live")
async def liveness_probe() -> dict[str, Any]:
    """Detailed liveness probe for Kubernetes.

    This endpoint is designed for Kubernetes liveness probes.
    It checks if the application process is alive and responding.
    Failure indicates the container should be restarted.

    Returns:
        Structured response with timestamp and service info.
    """
    return _build_health_response(
        status="alive",
        details={
            "version": getattr(settings, "VERSION", "1.0.0"),
            "environment": settings.ENVIRONMENT,
        },
    )


@router.get("/health/ready", response_model=None)
async def readiness_probe(
    db: DBSession,
    redis: Redis,
) -> dict[str, Any] | JSONResponse:
    """Readiness probe for Kubernetes.

    This endpoint checks if all dependencies are ready to handle traffic.
    It verifies database connections, Redis, and other critical services.
    Failure indicates traffic should be temporarily diverted.

    Checks performed:
    - Database connectivity
    - Redis connectivity

    Returns:
        Structured response with individual check results.
        Returns 503 if any critical check fails.
    """
    checks: dict[str, dict[str, Any]] = {}
    # Database check
    try:
        start = datetime.now(UTC)
        await db.execute(text("SELECT 1"))
        latency_ms = (datetime.now(UTC) - start).total_seconds() * 1000
        checks["database"] = {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "type": "postgresql",
        }
    except Exception as e:
        checks["database"] = {
            "status": "unhealthy",
            "error": str(e),
            "type": "postgresql",
        }
    # Redis check
    try:
        start = datetime.now(UTC)
        is_healthy = await redis.ping()
        latency_ms = (datetime.now(UTC) - start).total_seconds() * 1000
        if is_healthy:
            checks["redis"] = {
                "status": "healthy",
                "latency_ms": round(latency_ms, 2),
            }
        else:
            checks["redis"] = {
                "status": "unhealthy",
                "error": "Ping failed",
            }
    except Exception as e:
        checks["redis"] = {
            "status": "unhealthy",
            "error": str(e),
        }

    # Determine overall health
    all_healthy = (
        all(check.get("status") == "healthy" for check in checks.values()) if checks else True
    )

    response_data = _build_health_response(
        status="ready" if all_healthy else "not_ready",
        checks=checks,
    )

    if not all_healthy:
        return JSONResponse(status_code=503, content=response_data)

    return response_data


# Backward compatibility - keep /ready endpoint
@router.get("/ready", response_model=None)
async def readiness_check(
    db: DBSession,
    redis: Redis,
) -> dict[str, Any] | JSONResponse:
    """Readiness check (alias for /health/ready).

    Deprecated: Use /health/ready instead.
    """
    return await readiness_probe(
        db=db,
        redis=redis,
    )
