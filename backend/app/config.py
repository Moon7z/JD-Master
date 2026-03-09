from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "JD Master Resume Optimizer"
    app_env: str = "dev"
    cors_origins: str = Field(default="http://localhost:5173")

    ai_provider: str = "mock"
    doubao_api_key: str | None = None
    doubao_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    doubao_model: str = "doubao-seed-1-6-250615"

    request_timeout_seconds: int = 20
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
