from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    redis_url: str

    github_webhook_secret: str = ""
    stripe_webhook_secret: str = ""

    max_retry_attempts: int = 5
    retry_base_delay_seconds: int = 10


settings = Settings()
