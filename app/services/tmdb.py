#!/usr/bin/env python3
"""
Async TMDb API client.
Fetches movie releases for a given region and month, enriches each movie
with cast, trailer, and release type, then upserts into MongoDB.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import httpx

from app.config import settings
from app.models.movie import CastMember, Movie, WatchProvider

TMDB_BASE = "https://api.themoviedb.org/3"
MAX_PAGES = 5

RELEASE_TYPE_MAP: Dict[int, str] = {
    1: "Premiere",
    2: "Theatrical (Limited)",
    3: "Theatrical",
    4: "Digital",
    5: "Physical",
    6: "TV/Streaming",
}


async def _get_genres(client: httpx.AsyncClient) -> Dict[int, str]:
    """Fetch genre id → name mapping from TMDb."""
    response = await client.get(
        f"{TMDB_BASE}/genre/movie/list",
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
    """Fetch a single page of discover/movie results. Returns (results, total_pages)."""
    response = await client.get(
        f"{TMDB_BASE}/discover/movie",
        params={
            "api_key": settings.tmdb_api_key,
            "region": region,
            "release_date.gte": start_date,
            "release_date.lte": end_date,
            "sort_by": "release_date.asc",
            "with_release_type": "2|3|4|5|6",
            "page": page,
        },
    )
    response.raise_for_status()
    data = response.json()
    return data["results"], data["total_pages"]


async def _fetch_movie_details(
    client: httpx.AsyncClient, movie_id: int
) -> Dict:
    """Fetch full movie details including credits, videos, release_dates."""
    response = await client.get(
        f"{TMDB_BASE}/movie/{movie_id}",
        params={
            "api_key": settings.tmdb_api_key,
            "append_to_response": "credits,videos,release_dates,watch/providers",
        },
    )
    response.raise_for_status()
    return response.json()


def _extract_cast(details: Dict) -> List[CastMember]:
    """Return top 5 billed cast members from enriched details dict."""
    cast = []
    credits = details.get("credits", {})
    for actor in credits.get("cast", [])[:5]:
        cast.append(CastMember(name=actor["name"], character=actor["character"]))
    return cast


def _extract_trailer_url(details: Dict) -> Optional[str]:
    """Return the first YouTube trailer URL, or None."""
    videos = details.get("videos", {}).get("results", [])
    for v in videos:
        if v.get("type") == "Trailer" and v.get("site") == "YouTube":
            return f"https://www.youtube.com/watch?v={v['key']}"
    return None


def _extract_release_type(details: Dict, region: str) -> str:
    """Resolve the release type string for the given region."""
    release_dates = details.get("release_dates", {}).get("results", [])
    for rd in release_dates:
        if rd["iso_3166_1"] == region:
            dates = rd.get("release_dates", [])
            if dates:
                return RELEASE_TYPE_MAP.get(dates[0]["type"], "Unknown")
    return "Unknown"


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
        # Prefer flatrate (subscription), fall back to rent then buy
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


def _parse_release_date(date_str: str) -> Optional[datetime]:
    """
    Parse a "YYYY-MM-DD" string into a UTC-aware datetime.
    Returns None for "TBA", empty string, or any unparseable value.
    MongoDB TTL index ignores documents where the indexed field is null.
    """
    if not date_str or date_str == "TBA":
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


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
    Fetch all movies for a region/month from TMDb, enrich each one,
    and upsert into MongoDB.  Returns the number of movies processed.
    """
    start_date, end_date = _month_date_range(year, month)
    print(f"[TMDb] Fetching {region} {year}-{month:02d} ({start_date} → {end_date})")

    async with httpx.AsyncClient(timeout=30.0) as client:
        genres_map = await _get_genres(client)

        # Collect raw movie stubs across all pages
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

        print(f"[TMDb] Found {len(all_stubs)} movies for {region} {year}-{month:02d}")

        upserted = 0
        for stub in all_stubs:
            try:
                details = await _fetch_movie_details(client, stub["id"])

                genres = [
                    genres_map.get(g["id"], g["name"])
                    for g in details.get("genres", [])
                ]

                movie_data = {
                    "tmdb_id": stub["id"],
                    "title": details["title"],
                    "release_date": stub.get("release_date") or "TBA",
                    "release_date_dt": _parse_release_date(
                        stub.get("release_date") or "TBA"
                    ),
                    "overview": details.get("overview", ""),
                    "poster_path": stub.get("poster_path"),
                    "backdrop_path": stub.get("backdrop_path"),
                    "vote_average": details.get("vote_average", 0.0),
                    "vote_count": details.get("vote_count", 0),
                    "runtime": details.get("runtime"),
                    "genres": genres,
                    "cast": _extract_cast(details),
                    "trailer_url": _extract_trailer_url(details),
                    "release_type": _extract_release_type(details, region),
                    "watch_providers": _extract_watch_providers(
                        details, settings.tmdb_regions
                    ),
                    "tmdb_url": f"https://www.themoviedb.org/movie/{stub['id']}",
                    "fetched_at": datetime.now(timezone.utc),
                }

                # Upsert: update existing document or insert new one.
                # Merge the regions list so a movie found in both US and GB
                # accumulates regions=["US","GB"] rather than overwriting.
                existing = await Movie.find_one(Movie.tmdb_id == stub["id"])
                if existing:
                    merged_regions = list(
                        set(existing.regions) | {region}
                    )
                    await existing.set(
                        {**movie_data, "regions": merged_regions}
                    )
                else:
                    movie = Movie(**movie_data, regions=[region])
                    await movie.insert()

                upserted += 1

            except Exception as e:
                print(f"[TMDb] Error enriching '{stub.get('title', stub['id'])}': {e}")
                continue

    print(f"[TMDb] Upserted {upserted} movies for {region} {year}-{month:02d}")
    return upserted
