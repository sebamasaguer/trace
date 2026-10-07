from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ReciclaTrace API"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://recicla:recicla@db:5432/recicla"
    secret_key: str = "change-this-secret-in-production"
    access_token_minutes: int = 720
    cors_origins: str = "http://localhost:3210"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
