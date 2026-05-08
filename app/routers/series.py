#!/usr/bin/env python3
"""
Series routes — main grid page and detail page.
Filtering and sorting are handled server-side via MongoDB queries.
"""

from typing import List, Optional

from beanie.operators import In
from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.models.series import Series

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


async def _last_fetched_str() -> Optional[str]:
    """Return a formatted string of the most recent fetched_at timestamp, or None."""
    latest = await Series.find().sort("-fetched_at").first_or_none()
    if latest and latest.fetched_at:
        return latest.fetched_at.strftime("%d %b %Y %H:%M UTC")
    return None


@router.get("/series", response_class=HTMLResponse)
async def series_index(
    request: Request,
    genre: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    provider: Optional[str] = Query(default=None),
    sort: str = Query(default="first_air_date"),
) -> HTMLResponse:
    """
    Main series grid page.  All filtering is done in MongoDB.
    Query params:
        genre    — filter by genre name (exact match)
        status   — filter by series status (e.g. "Returning Series")
        region   — filter by region code, e.g. "US" or "GB"
        provider — filter by watch provider name, e.g. "Netflix"
        sort     — one of: first_air_date, vote_average, title
    """
    query = Series.find()

    if genre:
        query = query.find(In(Series.genres, [genre]))
    if status:
        query = query.find(Series.status == status)
    if region:
        query = query.find(In(Series.regions, [region]))
    if provider:
        query = query.find({"watch_providers.provider_name": provider})

    sort_field = {
        "first_air_date": "+first_air_date",
        "vote_average": "-vote_average",
        "title": "+title",
    }.get(sort, "+first_air_date")

    series_list: List[Series] = await query.sort(sort_field).to_list()

    # Build filter option lists for the UI dropdowns — filter out None values
    all_genres: List[str] = [g for g in await Series.distinct("genres") if g is not None]
    all_statuses: List[str] = [s for s in await Series.distinct("status") if s is not None]
    all_regions: List[str] = [r for r in await Series.distinct("regions") if r is not None]
    all_providers: List[str] = sorted([
        p for p in await Series.distinct("watch_providers.provider_name") if p is not None
    ])

    last_fetched = await _last_fetched_str()

    return templates.TemplateResponse(
        request,
        "series/index.html",
        {
            "request": request,
            "series_list": series_list,
            "all_genres": sorted(all_genres),
            "all_statuses": sorted(all_statuses),
            "all_regions": sorted(all_regions),
            "all_providers": all_providers,
            "active_genre": genre,
            "active_status": status,
            "active_region": region,
            "active_provider": provider,
            "active_sort": sort,
            "last_fetched": last_fetched,
        },
    )


@router.get("/series/{tmdb_id}", response_class=HTMLResponse)
async def series_detail(request: Request, tmdb_id: int) -> HTMLResponse:
    """Detail page for a single TV series."""
    series = await Series.find_one(Series.tmdb_id == tmdb_id)
    if not series:
        return templates.TemplateResponse(
            request,
            "404.html",
            {"request": request, "last_fetched": None},
            status_code=404,
        )

    last_fetched = await _last_fetched_str()
    return templates.TemplateResponse(
        request,
        "series/detail.html",
        {"request": request, "series": series, "last_fetched": last_fetched},
    )
