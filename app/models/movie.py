#!/usr/bin/env python3
"""
Beanie document model for movies.
CastMember is an embedded sub-document (no separate collection).
"""

from datetime import datetime, timezone
from typing import List, Optional

from beanie import Document
from pydantic import BaseModel, Field
from pymongo import IndexModel, ASCENDING, DESCENDING


class CastMember(BaseModel):
    """Embedded model — top 5 billed cast members per movie."""

    name: str
    character: str


class Movie(Document):
    """
    Canonical movie record.  Upserted by tmdb_id on every fetch run.
    The regions field accumulates all regions the movie was found in.
    """

    tmdb_id: int
    title: str
    release_date: Optional[str] = None   # "YYYY-MM-DD" or "TBA"
    overview: str = ""
    poster_path: Optional[str] = None    # e.g. "/abc123.jpg"
    backdrop_path: Optional[str] = None
    vote_average: float = 0.0
    vote_count: int = 0
    runtime: Optional[int] = None        # minutes
    genres: List[str] = Field(default_factory=list)
    cast: List[CastMember] = Field(default_factory=list)          # top 5 billed actors
    trailer_url: Optional[str] = None    # YouTube URL or None
    release_type: str = "Unknown"        # "Theatrical", "Digital", etc.
    tmdb_url: str = ""
    regions: List[str] = Field(default_factory=list)             # ["US", "GB"] — merged across fetches
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "movies"
        indexes = [
            IndexModel([("tmdb_id", ASCENDING)], unique=True),
            IndexModel([("release_date", ASCENDING)]),
            IndexModel([("genres", ASCENDING)]),
            IndexModel([("release_type", ASCENDING)]),
            IndexModel([("vote_average", DESCENDING)]),
            IndexModel([("regions", ASCENDING)]),
        ]
