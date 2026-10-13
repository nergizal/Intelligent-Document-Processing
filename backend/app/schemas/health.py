"""Sağlık kontrolü (health-check) yanıt şeması."""

from datetime import datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    database: str
    timestamp: datetime
