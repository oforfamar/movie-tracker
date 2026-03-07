#!/usr/bin/env python3
"""
Async Radarr API client.
Handles folder listing, quality profile resolution, movie lookup,
and adding movies to Radarr.
"""

from typing import Dict, List, Optional

import httpx

from app.config import settings


def _headers() -> Dict[str, str]:
    return {"X-Api-Key": settings.radarr_api_key, "Content-Type": "application/json"}


async def get_root_folders() -> List[Dict]:
    """
    Return all root folders configured in Radarr.
    Each dict has at minimum: id, path, freeSpace.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{settings.radarr_url}/api/v3/rootfolder",
            headers=_headers(),
        )
        response.raise_for_status()
        return response.json()


async def _get_quality_profile_id(client: httpx.AsyncClient) -> Optional[int]:
    """Resolve the numeric ID for the configured quality profile name."""
    response = await client.get(
        f"{settings.radarr_url}/api/v3/qualityprofile",
        headers=_headers(),
    )
    response.raise_for_status()
    for profile in response.json():
        if profile["name"] == settings.radarr_quality_profile:
            return profile["id"]
    return None


async def _lookup_by_tmdb_id(
    client: httpx.AsyncClient, tmdb_id: int
) -> Optional[Dict]:
    """
    Check if a movie already exists in Radarr by TMDb ID.
    Returns the Radarr movie dict if found, None otherwise.
    Requires a pre-opened AsyncClient (caller owns the session).
    """
    response = await client.get(
        f"{settings.radarr_url}/api/v3/movie",
        headers=_headers(),
    )
    response.raise_for_status()
    for movie in response.json():
        if movie.get("tmdbId") == tmdb_id:
            return movie
    return None


async def lookup_by_tmdb_id(tmdb_id: int) -> Optional[Dict]:
    """
    Public wrapper — check if a movie exists in Radarr by TMDb ID.
    Opens its own client session.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        return await _lookup_by_tmdb_id(client, tmdb_id)


async def add_movie(tmdb_id: int, title: str, year: int, folder_path: str) -> Dict:
    """
    Add a movie to Radarr.

    Returns a dict with keys:
        success (bool), message (str), radarr_id (int | None)

    Raises httpx.HTTPStatusError on Radarr API errors.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        # Check if already present
        existing = await _lookup_by_tmdb_id(client, tmdb_id)
        if existing:
            return {
                "success": False,
                "already_exists": True,
                "message": f"'{title}' is already in Radarr.",
                "radarr_id": existing.get("id"),
            }

        # Resolve quality profile
        quality_profile_id = await _get_quality_profile_id(client)
        if quality_profile_id is None:
            return {
                "success": False,
                "already_exists": False,
                "message": (
                    f"Quality profile '{settings.radarr_quality_profile}' "
                    "not found in Radarr. Check RADARR_QUALITY_PROFILE in .env."
                ),
                "radarr_id": None,
            }

        # Lookup TMDb metadata via Radarr's own lookup endpoint
        lookup_response = await client.get(
            f"{settings.radarr_url}/api/v3/movie/lookup/tmdb",
            params={"tmdbId": tmdb_id},
            headers=_headers(),
        )
        lookup_response.raise_for_status()
        movie_lookup = lookup_response.json()

        payload = {
            **movie_lookup,
            "qualityProfileId": quality_profile_id,
            "rootFolderPath": folder_path,
            "monitored": True,
            "addOptions": {
                "searchForMovie": True,
            },
        }

        add_response = await client.post(
            f"{settings.radarr_url}/api/v3/movie",
            json=payload,
            headers=_headers(),
        )
        add_response.raise_for_status()
        result = add_response.json()

        return {
            "success": True,
            "already_exists": False,
            "message": f"'{title}' added to Radarr successfully.",
            "radarr_id": result.get("id"),
        }
