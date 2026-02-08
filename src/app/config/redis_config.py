from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDIS_")

    HOST: str = "localhost"
    PORT: int = 6379
    USERNAME: str = "default"
    PASSWORD: SecretStr
    DB: int = 0


redis_settings = RedisSettings()  # type: ignore[call-arg]
