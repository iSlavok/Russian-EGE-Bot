from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DB_")

    HOST: str = "postgres"
    PORT: int = 5432
    NAME: str
    USER: str
    PASS: SecretStr
    DRIVER: str = "postgresql+asyncpg"

    POOL_SIZE: int = 20
    MAX_OVERFLOW: int = 30
    POOL_TIMEOUT: int = 10
    POOL_RECYCLE: int = 1800


database_settings = DatabaseSettings()  # type: ignore[call-arg]
