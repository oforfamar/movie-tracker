#!/usr/bin/env python3
"""
FastAPI application entry point.
Registers the lifespan context (DB init, scheduler), mounts static files,
and includes all routers.
"""

import asyncio
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.models.movie import Movie
from app.models.series import Series
from app.routers import movies as movies_router
from app.routers import radarr as radarr_router
from app.routers import series as series_router
from app.routers import sonarr as sonarr_router
from app.scheduler import daily_fetch

DB_INIT_MAX_TRIES = 5
DB_INIT_RETRY_DELAY = 5  # seconds


async def _init_db_with_retry() -> None:
    """Call init_db(), retrying when MongoDB or DNS isn't reachable yet."""
    for attempt in range(1, DB_INIT_MAX_TRIES + 1):
        try:
            await init_db()
            return
        except Exception as e:
            print(f"[App] DB init failed ({attempt}/{DB_INIT_MAX_TRIES}): {e}")
            if attempt == DB_INIT_MAX_TRIES:
                raise
            await asyncio.sleep(DB_INIT_RETRY_DELAY)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB, start scheduler. Shutdown: stop scheduler."""
    await _init_db_with_retry()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        daily_fetch,
        trigger="cron",
        hour=settings.fetch_hour,
        minute=0,
        id="daily_fetch",
        replace_existing=True,
    )
    scheduler.start()

    # Seed data immediately on first boot so the UI isn't blank
    movie_count = await Movie.count()
    series_count = await Series.count()
    if movie_count == 0 and series_count == 0:
        print("[App] Empty database — running initial fetch...")
        asyncio.create_task(daily_fetch())

    yield

    scheduler.shutdown(wait=False)


app = FastAPI(
    title="Movie Tracker",
    description="Plex-style upcoming movie and series tracker with Radarr/Sonarr integration.",
    version="3.0.0",
    lifespan=lifespan,
)

# Serve static files (JS, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Routers
app.include_router(movies_router.router)
app.include_router(radarr_router.router)
app.include_router(series_router.router)
app.include_router(sonarr_router.router)


@app.post("/admin/fetch", tags=["admin"])
async def trigger_fetch() -> dict:
    """Manually trigger the daily TMDb fetch job. No auth — internal use only."""
    asyncio.create_task(daily_fetch())
    return {"message": "Fetch job started in background."}
