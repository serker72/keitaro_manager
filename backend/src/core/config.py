"""Application settings loaded from environment via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings with defaults matching docker-compose postgres service."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_ENVIRONMENT: str = "loc"
    PROJECT_NAME: str = "keitaro_manager"

    # PostgreSQL
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "keitaro_manager"
    POSTGRES_PASSWORD: str = "secret"
    POSTGRES_DB: str = "keitaro_manager"

    # Keitaro API
    KEITARO_BASE_URL: str = "http://localhost/admin"
    KEITARO_API_KEY: str = ""

    @property
    def keitaro_base_url(self) -> str:
        return self.KEITARO_BASE_URL

    @property
    def keitaro_api_key(self) -> str:
        return self.KEITARO_API_KEY

    @property
    def database_url(self) -> str:
        """Build async database URL using psycopg3 dialect."""
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
