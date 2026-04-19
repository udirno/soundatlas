from typing import List
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://soundatlas_user:soundatlas_password@localhost:5432/soundatlas_db"

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def fix_async_url(cls, v: str) -> str:
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
    REDIS_URL: str = "redis://localhost:6379"
    SPOTIFY_CLIENT_ID: str = ""
    SPOTIFY_CLIENT_SECRET: str = ""
    ANTHROPIC_API_KEY: str = ""
    CORS_ORIGINS: str = "http://localhost:3000"
    APP_NAME: str = "SoundAtlas API"
    DEBUG: bool = True

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
