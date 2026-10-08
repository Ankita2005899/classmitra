"""Reads settings from environment variables (and from backend/.env while developing).

Secrets such as API keys live ONLY here, on the server. They are never put in
HTML or JavaScript, because anyone can read those files in the browser.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Reads backend/.env when you run the server from the backend/ folder.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    # Websites allowed to call this API from a browser (comma separated).
    allowed_origins: str = (
        "http://localhost:5500,http://127.0.0.1:5500,https://ankita2005899.github.io"
    )
    gemini_api_key: str = ""  # free key from Google AI Studio (used from Phase 2)

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
