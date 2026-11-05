from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

base_directory = Path(__file__).parent

env_file = base_directory.parent / ".env.test"


class AdminTestSettings(BaseSettings):
    """Base configuration class with common settings"""

    model_config = SettingsConfigDict(env_file=env_file, extra="ignore")

    db_host: str
    db_port: int = 5432
    db_name: str = Field(default="insertleft", validation_alias="__ignore_db_name__")
    db_super_user: str
    db_super_password: str

    @computed_field
    @property
    def superuser_database_url(self) -> str:
        return f"postgresql://{self.db_super_user}:{self.db_super_password}@{self.db_host}:{self.db_port}/{self.db_name}"
