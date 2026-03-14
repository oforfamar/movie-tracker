#!/usr/bin/env python3
"""
Sonarr routes — folder listing and series push endpoint.
"""

from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.models.series import Series
from app.services import sonarr as sonarr_service

router = APIRouter(prefix="/sonarr")


@router.get("/folders")
async def get_folders() -> JSONResponse:
    """
    Return available Sonarr root folders.
    The UI populates the modal dropdown from this endpoint.
    """
    try:
        folders = await sonarr_service.get_root_folders()
        simplified = [
            {"path": f["path"], "label": f["path"], "free_space": f.get("freeSpace", 0)}
            for f in folders
        ]
        return JSONResponse(content={"folders": simplified})
    except Exception as e:
        return JSONResponse(
            status_code=502,
            content={"error": f"Could not reach Sonarr: {e}"},
        )


class AddToSonarrRequest(BaseModel):
    folder_path: str


@router.post("/series/{tmdb_id}/add")
async def add_series_to_sonarr(
    tmdb_id: int, body: AddToSonarrRequest
) -> JSONResponse:
    """
    Push a series to Sonarr using the chosen root folder.
    Returns JSON: {success, already_exists, message, sonarr_id}
    """
    series = await Series.find_one(Series.tmdb_id == tmdb_id)
    if not series:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "Series not found in local database."},
        )

    # Extract first air year from first_air_date field
    year: Optional[int] = None
    if series.first_air_date and series.first_air_date != "TBA":
        try:
            year = int(series.first_air_date[:4])
        except ValueError:
            pass

    try:
        result = await sonarr_service.add_series(
            tmdb_id=tmdb_id,
            title=series.title,
            year=year or 0,
            folder_path=body.folder_path,
        )
        status = 200 if result["success"] or result.get("already_exists") else 502
        return JSONResponse(status_code=status, content=result)
    except Exception as e:
        return JSONResponse(
            status_code=502,
            content={
                "success": False,
                "already_exists": False,
                "message": f"Sonarr error: {e}",
                "sonarr_id": None,
            },
        )
