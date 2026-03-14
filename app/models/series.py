#!/usr/bin/env python3
"""
Beanie document model for TV series.
Reuses CastMember and WatchProvider embedded models from movie.py.
"""

from datetime import datetime, timezone
from typing import List, Optional

from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel

from app.models.movie import CastMember, WatchProvider


class Series(Document):
    """
    Canonical TV series record.  Upserted by tmdb_id on every fetch run.
    The regions field accumulates all regions the series was found in.
    """

    tmdb_id: int
    title: str
    first_air_date: Optional[str] = None       # "YYYY-MM-DD" or "TBA"
    overview: str = ""
    poster_path: Optional[str] = None           # e.g. "/abc123.jpg"
    backdrop_path: Optional[str] = None
    vote_average: float = 0.0
    vote_count: int = 0
    number_of_seasons: Optional[int] = None
    number_of_episodes: Optional[int] = None
    status: str = "Unknown"                     # "Returning Series", "Ended", etc.
    genres: List[str] = Field(default_factory=list)
    cast: List[CastMember] = Field(default_factory=list)           # top 5 billed actors
    trailer_url: Optional[str] = None           # YouTube URL or None
    tmdb_url: str = ""
    regions: List[str] = Field(default_factory=list)               # ["US", "GB"] — merged across fetches
    watch_providers: List[WatchProvider] = Field(default_factory=list)  # streaming / rental providers
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "series"
        indexes = [
            IndexModel([("tmdb_id", ASCENDING)], unique=True),
            IndexModel([("first_air_date", ASCENDING)]),
            IndexModel([("fetched_at", ASCENDING)], expireAfterSeconds=7776000),
            IndexModel([("genres", ASCENDING)]),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("vote_average", DESCENDING)]),
            IndexModel([("regions", ASCENDING)]),
            IndexModel([("watch_providers.provider_name", ASCENDING)]),
        ]
