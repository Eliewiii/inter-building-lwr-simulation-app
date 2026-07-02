"""Configuration for the API."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration Setting for the API."""

    storage_quota_mb: int = 50
    container_data_path: str = "/app/data"

    # Centralize your API routing settings here
    api_v1_prefix: str = "/api/v1"
    # Authentication settings with default values for local development.
    jwt_secret_key: str = "fallback-local-development-key-never-use-in-prod"
    jwt_algorithm: str = "HS256"
    # Dynamic Celery Routing Queues
    celery_fast_lane_queue: str = "fast_lane"
    celery_slow_lane_queue: str = "slow_lane"

    dev_mode: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
