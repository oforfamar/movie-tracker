#!/usr/bin/env python3
"""
Database initialisation — async PyMongo client and Beanie ODM setup.
Call init_db() once at application startup inside the FastAPI lifespan.
"""

from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.config import settings


async def init_db() -> None:
    """Initialise the async MongoDB client and register document models."""
    # Import here to avoid circular imports at module load time
    from app.models.movie import Movie
    from app.models.series import Series

    client = AsyncMongoClient(settings.mongodb_uri)
    database = client.get_default_database()

    try:
        await init_beanie(
            database=database,
            document_models=[Movie, Series],
            allow_index_dropping=True,
        )
    except Exception:
        # Don't leave a half-open client behind when the caller retries
        await client.close()
        raise
