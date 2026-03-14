#!/usr/bin/env python3
"""
APScheduler job definitions.
The daily_fetch job is registered in app/main.py's lifespan context.
"""

from datetime import datetime, timezone

from app.config import settings
from app.services.tmdb import fetch_and_upsert as fetch_movies
from app.services.tmdb_series import fetch_and_upsert as fetch_series


def _current_and_next_months():
    """Return [(year, month), (year, month)] for current and next month."""
    now = datetime.now(timezone.utc)
    year, month = now.year, now.month
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1
    return [(year, month), (next_year, next_month)]


async def daily_fetch() -> None:
    """
    Scheduled job: fetch current + next month for every configured region.
    Runs sequentially (one region/month at a time) to respect TMDb rate limits.
    Fetches both movies and TV series.
    """
    print(f"[Scheduler] daily_fetch started at {datetime.now(timezone.utc).isoformat()}")
    months = _current_and_next_months()
    total_movies = 0
    total_series = 0

    for region in settings.tmdb_regions:
        for year, month in months:
            try:
                count = await fetch_movies(region, year, month)
                total_movies += count
            except Exception as e:
                print(f"[Scheduler] fetch_movies failed for {region} {year}-{month:02d}: {e}")

            try:
                count = await fetch_series(region, year, month)
                total_series += count
            except Exception as e:
                print(f"[Scheduler] fetch_series failed for {region} {year}-{month:02d}: {e}")

    print(
        f"[Scheduler] daily_fetch complete — "
        f"{total_movies} movies and {total_series} series upserted."
    )
