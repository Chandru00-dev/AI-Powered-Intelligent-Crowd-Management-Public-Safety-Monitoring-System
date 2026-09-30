import os
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "AI-Powered Intelligent Crowd Management and Public Safety Monitoring System"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api"

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    SECRET_KEY: str = "crowd-safety-super-secret-key-change-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/crowd_safety_db"
    SQLITE_FALLBACK_URL: str = "sqlite:///./crowd_safety.db"

    DEFAULT_ADMIN_EMAIL: str = "admin@crowdsafety.ai"
    DEFAULT_ADMIN_PASSWORD: str = "Admin@12345"
    DEFAULT_ADMIN_NAME: str = "System Administrator"

    DEFAULT_OPERATOR_EMAIL: str = "operator@crowdsafety.ai"
    DEFAULT_OPERATOR_PASSWORD: str = "Operator@12345"
    DEFAULT_OPERATOR_NAME: str = "Control Room Operator"

    MAX_STREAM_FPS: int = 25
    JPEG_QUALITY: int = 75
    RTSP_TIMEOUT_MS: int = 5000

    CORS_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000,http://localhost:5500,http://127.0.0.1:5500,http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return ["*"]

settings = Settings()
