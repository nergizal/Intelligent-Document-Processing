"""v1 API router aggregator - yeni endpoint modülleri burada dahil edilir."""

from fastapi import APIRouter

from app.api.v1.endpoints import health

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
