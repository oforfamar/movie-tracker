#!/usr/bin/env python3
"""
Application configuration — reads from environment variables or .env file.
All settings are validated by Pydantic at startup.
"""

from typing import List

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # TMDb
    tmdb_api_key: str
    # Stored as a raw comma-separated string; use .tmdb_regions for the list.
    # pydantic-settings v2 JSON-decodes List fields from env before validators
    # run, which breaks plain "US,GB" values.  Keeping it as str sidesteps that.
    # AliasChoices lets the env var remain TMDB_REGIONS (no .env changes needed).
    tmdb_regions_raw: str = Field(
        default="US,GB",
        validation_alias=AliasChoices("tmdb_regions", "tmdb_regions_raw"),
    )

    # MongoDB
    mongodb_uri: str

    # Radarr
    radarr_url: str
    radarr_api_key: str
    radarr_quality_profile: str = "4K-2160p"

    # Sonarr
    sonarr_url: str
    sonarr_api_key: str
    sonarr_quality_profile: str = "WEB-1080p"

    # App
    fetch_hour: int = 3
    port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_ignore_empty=True,
        populate_by_name=True,
    )

    @field_validator("radarr_url", "sonarr_url", mode="before")
    @classmethod
    def strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")

    @property
    def tmdb_regions(self) -> List[str]:
        """Parsed list of region codes from the raw comma-separated env var."""
        return [r.strip().upper() for r in self.tmdb_regions_raw.split(",") if r.strip()]


settings = Settings()
