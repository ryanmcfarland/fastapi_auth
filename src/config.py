import os

from functools import lru_cache
from pathlib import Path
from typing import Optional, List, Annotated

from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings

base_directory = Path(__file__).parent

env_file = os.environ.get("FASTAPI_ENV_FILE", base_directory.parent.joinpath(".env").as_posix())

"""
Required JWT Constants - Not to be committed
SECRET_KEY
ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS
"""


class BaseConfig(BaseSettings):
    """Base configuration class with common settings"""

    model_config = ConfigDict(env_file=env_file, case_sensitive=True, extra="ignore")

    # Application settings
    APP_NAME: str = "FastAPI Application"
    APP_VERSION: str = "1.0.0"
    SHOW_DOCS: bool = False

    # Logging
    LOG_DIRECTORY: str
    LOG_LEVEL: str = "INFO"
    LOG_INCLUDE_OPTIONAL: bool = False

    # Common Config
    CODE_DIR: Annotated[Path, "Path: App Directory"] = base_directory
    REPO_DIR: Annotated[Path, "Path: Base Repository"] = CODE_DIR.parent

    # Database settings - Example str: "postgresql://user:password@localhost/dbname"
    DATABASE_URL: Optional[str] = None
    DB_POOL_SIZE: int = 2

    # Security settings
    SECRET_KEY: str
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # Cookie Settings
    HTTP_ONLY: bool = True
    SECURE_COOKIES: bool = True

    @field_validator("LOG_DIRECTORY")
    def create_log_directory(cls, v):
        os.makedirs(v, exist_ok=True)
        return v


class DevelopmentConfig(BaseConfig):
    """Development configuration"""

    DEBUG: bool = True
    TESTING: bool = False
    SHOW_DOCS: bool = True

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10
    SECRET_KEY: str = "my - secret - key"


class TestingConfig(BaseConfig):
    """Development configuration"""

    DEBUG: bool = True
    TESTING: bool = True

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1
    SECRET_KEY: str = "my - secret - test - key"

    SECURE_COOKIES: bool = False
    HTTP_ONLY: bool = False


class ProductionConfig(BaseConfig):
    """Production configuration"""

    DEBUG: bool = False
    TESTING: bool = False

    LOG_LEVEL: str = "WARNING"


# Factory function to get the appropriate config
def get_config() -> BaseConfig:
    """
    Factory function to return the appropriate configuration based on environment.
    Set ENVIRONMENT variable to 'development' or 'production'
    """
    env = os.getenv("ENVIRONMENT", "development").lower()

    if env == "production":
        return ProductionConfig()
    elif env == "testing":
        return TestingConfig()
    else:
        return DevelopmentConfig()


@lru_cache()
def get_settings():
    return get_config()
