from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Drive Spark Rent API"
    APP_ENV: Literal["development", "staging", "production", "test"] = "development"
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: list[AnyHttpUrl] = Field(default_factory=list)
    BACKEND_URL: str = "http://localhost:8000"

    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "drive_spark_rent"

    JWT_SECRET_KEY: str = "change-this-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_SECURE: bool = False
    SMTP_USER: str = "smtp-user"
    SMTP_PASSWORD: str = "smtp-password"
    SMTP_FROM_EMAIL: str = "Drive Spark Rent <no-reply@example.com>"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
