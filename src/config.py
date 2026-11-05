"""
Pydantic Settings Configuration Module

This module defines configuration classes for both FastAPI and Celery applications.

Key behaviors:
- BaseSettings (from pydantic-settings) automatically loads environment variables
  and .env files. It searches for a .env file in the current directory by default.
- SettingsConfigDict is used to customize this behavior via the model_config attribute,
  allowing you to specify a custom env_file path (like .env at the repo root) and
  other settings such as env_prefix, extra field handling, etc.
- The FASTAPI_ENV_FILE environment variable can override the default .env path.

The configuration classes are organized by environment:
- DevelopmentConfig: Debug mode enabled, relaxed security settings
- TestingConfig: Testing-specific settings (eager task execution, no secure cookies)
- ProductionConfig: Strict security and performance settings

Required JWT Constants - Not to be committed
SECRET_KEY
ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS
"""

import os

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import TypeVar, Self

from pydantic import Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

base_directory: Path = Path(__file__).parent

env_file: Path | str = os.environ.get("FASTAPI_ENV_FILE", base_directory.parent / ".env")

env = os.getenv("ENVIRONMENT", "development").lower()


class CaseInsensitiveStrEnum(StrEnum):
    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            return cls.__members__.get(value.upper())
        return None


class ProcessType(CaseInsensitiveStrEnum):
    FASTAPI = "fastapi"
    CELERY_WORKER = "celery_worker"
    CELERY_BEAT = "celery_beat"


class Environment(CaseInsensitiveStrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class SharedConfig(BaseSettings):
    """Shared configuration between FastAPI and Celery"""

    model_config = SettingsConfigDict(env_file=env_file, extra="ignore")

    debug: bool = False
    testing: bool = False
    env: Environment = Environment.DEVELOPMENT
    process_type: ProcessType = ProcessType.FASTAPI

    # Common Config
    code_directory: Path = Field(base_directory, description="Path: App Directory")
    repo_directory: Path = Field(base_directory.parent, description="Path: Base Repository")

    # Logging
    log_directory: Path | None = Field(default=None, description="Path: Log Directory")
    log_name: str | None = Field(default=None, description="str: Log File Name")
    log_level: str = "WARNING"
    log_include_optional: bool = False

    # Database Connections
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str
    db_user: str
    db_password: str

    # psycopg connection settings
    db_pool_size: int = 2

    # Security settings
    secret_key: str
    algorithm: str = "HS256"

    # Redis Settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    @model_validator(mode="after")
    def set_and_create_log_directory(self) -> Self:
        if self.log_directory is None:
            self.log_directory = self.repo_directory / "logs"
        self.log_directory.mkdir(exist_ok=True)
        return self

    @model_validator(mode="after")
    def set_log_name(self) -> Self:
        if self.log_name is None:
            self.log_name = self.process_type.value
        return self

    @computed_field
    @property
    def database_url(self) -> str:
        """Example str: "postgresql://user:password@localhost/dbname"""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @computed_field
    @property
    def redis_url(self) -> str:
        """Example str: "redis://localhost:6379/0"""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


class BaseConfig(SharedConfig):
    """Base configuration class with FastAPI-specific settings"""

    # Application settings
    app_name: str = "FastAPI Application"
    app_version: str = "1.0.0"
    show_docs: bool = False
    frontend_url: str = "http://localhost:3000"

    # Auth settings
    refresh_token_expire_days: int = 7
    access_token_expire_minutes: int = 60
    password_reset_token_expire_hours: int = 1

    # Cookie Settings
    access_token_cookie_name: str = "access_token"
    refresh_token_cookie_name: str = "refresh_token"
    http_only: bool = True
    secure_cookies: bool = True

    # Resend Email Settings
    resend_api_key: str | None = None
    resend_from_email: str = "noreply@mail.insertleft.com"


class DevelopmentConfig(BaseConfig):
    """Development configuration"""

    debug: bool = True
    show_docs: bool = True

    access_token_expire_minutes: int = 10
    secret_key: str = "my - secret - key"

    # The browser now receives the auth cookies directly from FastAPI over
    # http://localhost during development.
    secure_cookies: bool = False

    log_level: str = "INFO"


class TestingConfig(BaseConfig):
    """Testing configuration"""

    debug: bool = True
    testing: bool = True

    access_token_expire_minutes: int = 1
    secret_key: str = "my - secret - test - key"

    secure_cookies: bool = False
    http_only: bool = False

    log_level: str = "INFO"


class ProductionConfig(BaseConfig):
    """Production configuration"""

    pass


CONFIG_MAP: dict[str, type[BaseConfig]] = {
    "production": ProductionConfig,
    "testing": TestingConfig,
    "development": DevelopmentConfig,
}


T = TypeVar("T")


def _resolve_config(config_map: dict[str, type[T]], cli_overrides: dict | None = None) -> T:
    if cli_overrides is None:
        cli_overrides = {}

    config_class = config_map.get(env, config_map["development"])
    return config_class(**cli_overrides)


# Factory functions
def get_config(cli_overrides: dict | None = None) -> BaseConfig:
    """
    Factory function to return the appropriate FastAPI configuration based on environment.
    Set ENVIRONMENT variable to 'development', 'testing', or 'production'
    """
    return _resolve_config(CONFIG_MAP, cli_overrides)


@lru_cache()
def get_settings():
    return get_config()
