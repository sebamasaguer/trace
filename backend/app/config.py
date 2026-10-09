import hashlib
import hmac
from functools import lru_cache
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Valores de ejemplo publicados en el repo: nunca deben usarse para firmar.
INSECURE_SECRETS = {
    "change-this-secret-in-production",
    "change-me-in-production",
}
MIN_SECRET_LENGTH = 16


class Settings(BaseSettings):
    app_name: str = "ReciclaTrace API"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://recicla:recicla@db:5432/recicla"
    secret_key: str = "change-this-secret-in-production"
    # Clave independiente para firmar los QR. Si no se define, se deriva de
    # secret_key con HMAC y una etiqueta de dominio distinta.
    qr_secret_key: str | None = None
    access_token_minutes: int = 720
    cors_origins: str = "http://localhost:3210"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_secrets(self) -> "Settings":
        if self.secret_key in INSECURE_SECRETS or len(self.secret_key) < MIN_SECRET_LENGTH:
            raise ValueError(
                "SECRET_KEY inseguro: defina un valor propio de al menos "
                f"{MIN_SECRET_LENGTH} caracteres (no use el valor de ejemplo)."
            )
        if self.qr_secret_key:
            if self.qr_secret_key in INSECURE_SECRETS or len(self.qr_secret_key) < MIN_SECRET_LENGTH:
                raise ValueError(
                    f"QR_SECRET_KEY inseguro: defina un valor propio de al menos {MIN_SECRET_LENGTH} caracteres."
                )
            if self.qr_secret_key == self.secret_key:
                raise ValueError("QR_SECRET_KEY debe ser distinto de SECRET_KEY.")
        return self

    @property
    def qr_key(self) -> str:
        if self.qr_secret_key:
            return self.qr_secret_key
        return hmac.new(
            self.secret_key.encode(), b"recicla-trace:qr-label:v1", hashlib.sha256
        ).hexdigest()

    @property
    def cors_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
