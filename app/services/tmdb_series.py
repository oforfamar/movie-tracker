#!/usr/bin/env python3
"""
Async TMDb API client for TV series.
Fetches upcoming series for a given region and month, enriches each one
with cast, trailer, and watch providers, then upserts into MongoDB.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import httpx

from app.config import settings
from app.models.movie import CastMember, WatchProvider
from app.models.series import Series

TMDB_BASE = "https://api.themoviedb.org/3"
MAX_PAGES = 5


async def _get_genres(client: httpx.AsyncClient) -> Dict[int, str]:
    """Fetch TV genre id → name mapping from TMDb."""
    response = await client.get(
        f"{TMDB_BASE}/genre/tv/list",
        params={"api_key": settings.tmdb_api_key},
    )
    response.raise_for_status()
    return {g["id"]: g["name"] for g in response.json()["genres"]}


async def _fetch_page(
    client: httpx.AsyncClient,
    region: str,
    start_date: str,
    end_date: str,
    page: int,
) -> Tuple[List[Dict], int]:
    """Fetch a single page of discover/tv results. Returns (results, total_pages)."""
    response = await client.get(
        f"{TMDB_BASE}/discover/tv",
        params={
            "api_key": settings.tmdb_api_key,
            "with_origin_country": region,
            "air_date.gte": start_date,
            "air_date.lte": end_date,
            "sort_by": "first_air_date.asc",
            "page": page,
        },
    )
    response.raise_for_status()
    data = response.json()
    return data["results"], data["total_pages"]


async def _fetch_series_details(
    client: httpx.AsyncClient, series_id: int
) -> Dict:
    """Fetch full series details including credits, videos, and watch providers."""
    response = await client.get(
        f"{TMDB_BASE}/tv/{series_id}",
        params={
            "api_key": settings.tmdb_api_key,
            "append_to_response": "aggregate_credits,videos,watch/providers,content_ratings",
        },
    )
    response.raise_for_status()
    return response.json()


def _extract_cast(details: Dict) -> List[CastMember]:
    """
    Return top 5 billed cast members from enriched series details dict.
    TV series use aggregate_credits instead of credits.
    """
    cast = []
    # aggregate_credits groups a person's roles across all episodes
    agg = details.get("aggregate_credits", {})
    for actor in agg.get("cast", [])[:5]:
        roles = actor.get("roles", [])
        character = roles[0]["character"] if roles else ""
        cast.append(CastMember(name=actor["name"], character=character))
    return cast


def _extract_trailer_url(details: Dict) -> Optional[str]:
    """Return the first YouTube trailer URL, or None."""
    videos = details.get("videos", {}).get("results", [])
    for v in videos:
        if v.get("type") == "Trailer" and v.get("site") == "YouTube":
            return f"https://www.youtube.com/watch?v={v['key']}"
    return None


def _extract_watch_providers(
    details: Dict, regions: List[str]
) -> List[WatchProvider]:
    """
    Extract streaming/rental/purchase providers from the watch/providers
    sub-response for the configured regions.

    Preference order per region: flatrate → rent → buy.
    Deduplicates across regions by provider_id.
    """
    providers_by_region = (
        details.get("watch/providers", {}).get("results", {})
    )
    seen_ids: set = set()
    providers: List[WatchProvider] = []

    for region in regions:
        region_data = providers_by_region.get(region, {})
        entries = (
            region_data.get("flatrate")
            or region_data.get("rent")
            or region_data.get("buy")
            or []
        )
        for entry in entries:
            pid = entry.get("provider_id")
            if pid is None or pid in seen_ids:
                continue
            logo = entry.get("logo_path", "")
            name = entry.get("provider_name", "")
            if not logo or not name:
                continue
            seen_ids.add(pid)
            providers.append(
                WatchProvider(
                    provider_id=pid,
                    provider_name=name,
                    logo_path=logo,
                )
            )

    return providers


def _month_date_range(year: int, month: int) -> Tuple[str, str]:
    """Return (start_date, end_date) strings for a given year/month."""
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = datetime(year, month + 1, 1) - timedelta(days=1)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


async def fetch_and_upsert(region: str, year: int, month: int) -> int:
    """
    Fetch all TV series for a region/month from TMDb, enrich each one,
    and upsert into MongoDB.  Returns the number of series processed.
    """
    start_date, end_date = _month_date_range(year, month)
    print(f"[TMDb-TV] Fetching {region} {year}-{month:02d} ({start_date} → {end_date})")

    async with httpx.AsyncClient(timeout=30.0) as client:
        genres_map = await _get_genres(client)

        # Collect raw series stubs across all pages
        all_stubs: List[Dict] = []
        page = 1
        while True:
            results, total_pages = await _fetch_page(
                client, region, start_date, end_date, page
            )
            all_stubs.extend(results)
            if page >= total_pages or page >= MAX_PAGES:
                break
            page += 1

        print(f"[TMDb-TV] Found {len(all_stubs)} series for {region} {year}-{month:02d}")

        upserted = 0
        for stub in all_stubs:
            try:
                details = await _fetch_series_details(client, stub["id"])

                genres = [
                    genres_map.get(g["id"], g["name"])
                    for g in details.get("genres", [])
                ]

                first_air_date = stub.get("first_air_date") or "TBA"

                series_data = {
                    "tmdb_id": stub["id"],
                    "title": details.get("name", stub.get("name", "")),
                    "first_air_date": first_air_date,
                    "overview": details.get("overview", ""),
                    "poster_path": stub.get("poster_path"),
                    "backdrop_path": stub.get("backdrop_path"),
                    "vote_average": details.get("vote_average", 0.0),
                    "vote_count": details.get("vote_count", 0),
                    "number_of_seasons": details.get("number_of_seasons"),
                    "number_of_episodes": details.get("number_of_episodes"),
                    "status": details.get("status", "Unknown"),
                    "genres": genres,
                    "cast": _extract_cast(details),
                    "trailer_url": _extract_trailer_url(details),
                    "watch_providers": _extract_watch_providers(
                        details, settings.tmdb_regions
                    ),
                    "tmdb_url": f"https://www.themoviedb.org/tv/{stub['id']}",
                    "fetched_at": datetime.now(timezone.utc),
                }

                # Upsert: update existing document or insert new one.
                # Merge the regions list so a series found in both US and GB
                # accumulates regions=["US","GB"] rather than overwriting.
                existing = await Series.find_one(Series.tmdb_id == stub["id"])
                if existing:
                    merged_regions = list(
                        set(existing.regions) | {region}
                    )
                    await existing.set(
                        {**series_data, "regions": merged_regions}
                    )
                else:
                    series = Series(**series_data, regions=[region])
                    await series.insert()

                upserted += 1

            except Exception as e:
                print(f"[TMDb-TV] Error enriching '{stub.get('name', stub['id'])}': {e}")
                continue

    print(f"[TMDb-TV] Upserted {upserted} series for {region} {year}-{month:02d}")
    return upserted
