"""Sağlık kontrolü endpoint'i."""

from datetime import datetime, timezone

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.db.session import is_database_reachable
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Servis sağlık kontrolü")
def check_health() -> JSONResponse:
    """Servisin ve veritabanı bağlantısının durumunu döner."""
    database_ok = is_database_reachable()

    payload = HealthResponse(
        status="healthy" if database_ok else "unhealthy",
        database="connected" if database_ok else "disconnected",
        timestamp=datetime.now(timezone.utc),
    )

    http_status = status.HTTP_200_OK if database_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=http_status, content=payload.model_dump(mode="json"))
