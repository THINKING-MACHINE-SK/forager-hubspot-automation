from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    hubspot_access_token: str
    forager_api_key: str
    forager_base_url: str
    allowed_job_titles: str = "CEO,CTO,VP Engineering,Head of AI"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def job_titles(self) -> list[str]:
        return [
            title.strip()
            for title in self.allowed_job_titles.split(",")
            if title.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()