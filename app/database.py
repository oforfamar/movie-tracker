#!/usr/bin/env python3
"""
Database initialisation — Motor async client and Beanie ODM setup.
Call init_db() once at application startup inside the FastAPI lifespan.
"""

from typing import List

import motor.motor_asyncio
from beanie import init_beanie

from app.config import settings


async def init_db() -> None:
    """Initialise Motor client and register all Beanie document models."""
    # Import here to avoid circular imports at module load time
    from app.models.movie import Movie
    from app.models.series import Series

    client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongodb_uri)
    database = client.get_default_database()

    await init_beanie(
        database=database,
        document_models=[Movie, Series],
        allow_index_dropping=True,
    )
