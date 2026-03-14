#!/usr/bin/env python3
"""
Async Sonarr API client.
Handles folder listing, quality profile resolution, series lookup,
and adding series to Sonarr.
"""

from typing import Dict, List, Optional

import httpx

from app.config import settings


def _headers() -> Dict[str, str]:
    return {"X-Api-Key": settings.sonarr_api_key, "Content-Type": "application/json"}


async def get_root_folders() -> List[Dict]:
    """
    Return all root folders configured in Sonarr.
    Each dict has at minimum: id, path, freeSpace.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{settings.sonarr_url}/api/v3/rootfolder",
            headers=_headers(),
        )
        response.raise_for_status()
        return response.json()


async def _get_quality_profile_id(client: httpx.AsyncClient) -> Optional[int]:
    """Resolve the numeric ID for the configured quality profile name."""
    response = await client.get(
        f"{settings.sonarr_url}/api/v3/qualityprofile",
        headers=_headers(),
    )
    response.raise_for_status()
    for profile in response.json():
        if profile["name"] == settings.sonarr_quality_profile:
            return profile["id"]
    return None


async def _lookup_existing(
    client: httpx.AsyncClient, tmdb_id: int
) -> Optional[Dict]:
    """
    Check if a series already exists in Sonarr by searching the library.
    Sonarr stores series by TVDB ID, but the lookup endpoint accepts TMDb IDs.
    Returns the Sonarr series dict if found, None otherwise.
    Requires a pre-opened AsyncClient (caller owns the session).
    """
    response = await client.get(
        f"{settings.sonarr_url}/api/v3/series",
        headers=_headers(),
    )
    response.raise_for_status()
    # Sonarr may store tmdbId on each series record
    for series in response.json():
        if series.get("tmdbId") == tmdb_id:
            return series
    return None


async def _lookup_by_tmdb_id(
    client: httpx.AsyncClient, tmdb_id: int
) -> Optional[Dict]:
    """
    Use Sonarr's lookup endpoint to find series metadata by TMDb ID.
    This is used to get Sonarr-enriched metadata (including TVDB ID) before adding.
    Returns the first matching result or None.
    """
    response = await client.get(
        f"{settings.sonarr_url}/api/v3/series/lookup",
        params={"term": f"tmdb:{tmdb_id}"},
        headers=_headers(),
    )
    response.raise_for_status()
    results = response.json()
    if results:
        return results[0]
    return None


async def add_series(tmdb_id: int, title: str, year: int, folder_path: str) -> Dict:
    """
    Add a series to Sonarr.

    Returns a dict with keys:
        success (bool), already_exists (bool), message (str), sonarr_id (int | None)

    Raises httpx.HTTPStatusError on Sonarr API errors.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        # Check if already present in Sonarr library
        existing = await _lookup_existing(client, tmdb_id)
        if existing:
            return {
                "success": False,
                "already_exists": True,
                "message": f"'{title}' is already in Sonarr.",
                "sonarr_id": existing.get("id"),
            }

        # Resolve quality profile
        quality_profile_id = await _get_quality_profile_id(client)
        if quality_profile_id is None:
            return {
                "success": False,
                "already_exists": False,
                "message": (
                    f"Quality profile '{settings.sonarr_quality_profile}' "
                    "not found in Sonarr. Check SONARR_QUALITY_PROFILE in .env."
                ),
                "sonarr_id": None,
            }

        # Lookup series metadata via Sonarr's TMDb lookup endpoint
        series_lookup = await _lookup_by_tmdb_id(client, tmdb_id)
        if series_lookup is None:
            return {
                "success": False,
                "already_exists": False,
                "message": f"Could not find '{title}' in Sonarr's TMDb lookup.",
                "sonarr_id": None,
            }

        payload = {
            **series_lookup,
            "qualityProfileId": quality_profile_id,
            "rootFolderPath": folder_path,
            "monitored": True,
            "addOptions": {
                "searchForMissingEpisodes": True,
                "monitor": "all",
            },
        }

        add_response = await client.post(
            f"{settings.sonarr_url}/api/v3/series",
            json=payload,
            headers=_headers(),
        )
        add_response.raise_for_status()
        result = add_response.json()

        return {
            "success": True,
            "already_exists": False,
            "message": f"'{title}' added to Sonarr successfully.",
            "sonarr_id": result.get("id"),
        }
