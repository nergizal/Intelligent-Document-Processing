"""
Uygulama genelinde kullanılan ayarlar (Settings).

Pydantic v2 (pydantic-settings) kullanılarak .env dosyasından okunur.
Böylece tüm konfigürasyon tek bir yerden yönetilir ve kod içinde
`os.getenv(...)` çağrıları tekrarlanmaz.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    log_level: str = "INFO"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_v1_prefix: str = "/api/v1"
    cors_allowed_origins: str = "http://localhost:3000"

    database_url: str = "postgresql+psycopg2://idp_user:change_me@localhost:5432/idp_platform"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Settings nesnesini uygulama yaşam döngüsü boyunca tek sefer oluşturur."""
    return Settings()
