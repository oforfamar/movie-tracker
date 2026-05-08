#!/usr/bin/env python3
"""
Movie routes — main grid page and optional detail page.
Filtering and sorting are handled server-side via MongoDB queries.
"""

from typing import List, Optional

from beanie.operators import In
from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.models.movie import Movie

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


async def _last_fetched_str() -> Optional[str]:
    """Return a formatted string of the most recent fetched_at timestamp, or None."""
    latest = await Movie.find().sort("-fetched_at").first_or_none()
    if latest and latest.fetched_at:
        return latest.fetched_at.strftime("%d %b %Y %H:%M UTC")
    return None


@router.get("/", response_class=HTMLResponse)
async def redirect_to_movies() -> RedirectResponse:
    return RedirectResponse(url="/movies")


@router.get("/movies", response_class=HTMLResponse)
async def movies_index(
    request: Request,
    genre: Optional[str] = Query(default=None),
    release_type: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    provider: Optional[str] = Query(default=None),
    sort: str = Query(default="release_date"),
) -> HTMLResponse:
    """
    Main grid page.  All filtering is done in MongoDB.
    Query params:
        genre        — filter by genre name (exact match)
        release_type — filter by release type string
        region       — filter by region code, e.g. "US" or "GB"
        provider     — filter by watch provider name, e.g. "Netflix"
        sort         — one of: release_date, vote_average, title
    """
    query = Movie.find()

    if genre:
        query = query.find(In(Movie.genres, [genre]))
    if release_type:
        query = query.find(Movie.release_type == release_type)
    if region:
        query = query.find(In(Movie.regions, [region]))
    if provider:
        query = query.find({"watch_providers.provider_name": provider})

    sort_field = {
        "release_date": "+release_date",
        "vote_average": "-vote_average",
        "title": "+title",
    }.get(sort, "+release_date")

    movies: List[Movie] = await query.sort(sort_field).to_list()

    # Build filter option lists for the UI dropdowns — filter out None values
    # that can appear when a movie has an empty genres/regions array in MongoDB.
    all_genres: List[str] = [g for g in await Movie.distinct("genres") if g is not None]
    all_release_types: List[str] = [r for r in await Movie.distinct("release_type") if r is not None]
    all_regions: List[str] = [r for r in await Movie.distinct("regions") if r is not None]
    all_providers: List[str] = sorted([
        p for p in await Movie.distinct("watch_providers.provider_name") if p is not None
    ])

    # Last fetched timestamp — most recently upserted document
    last_fetched = await _last_fetched_str()

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "movies": movies,
            "all_genres": sorted(all_genres),
            "all_release_types": sorted(all_release_types),
            "all_regions": sorted(all_regions),
            "all_providers": all_providers,
            "active_genre": genre,
            "active_release_type": release_type,
            "active_region": region,
            "active_provider": provider,
            "active_sort": sort,
            "last_fetched": last_fetched,
        },
    )


@router.get("/movies/{tmdb_id}", response_class=HTMLResponse)
async def movie_detail(request: Request, tmdb_id: int) -> HTMLResponse:
    """Detail page for a single movie."""
    movie = await Movie.find_one(Movie.tmdb_id == tmdb_id)
    if not movie:
        return templates.TemplateResponse(
            request,
            "404.html",
            {"request": request, "last_fetched": None},
            status_code=404,
        )

    last_fetched = await _last_fetched_str()
    return templates.TemplateResponse(
        request,
        "detail.html",
        {"request": request, "movie": movie, "last_fetched": last_fetched},
    )
