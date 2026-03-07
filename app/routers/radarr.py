#!/usr/bin/env python3
"""
Radarr routes — folder listing and movie push endpoint.
"""

from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.models.movie import Movie
from app.services import radarr as radarr_service

router = APIRouter(prefix="/radarr")


@router.get("/folders")
async def get_folders() -> JSONResponse:
    """
    Return available Radarr root folders.
    The UI populates the modal dropdown from this endpoint.
    """
    try:
        folders = await radarr_service.get_root_folders()
        simplified = [
            {"path": f["path"], "label": f["path"], "free_space": f.get("freeSpace", 0)}
            for f in folders
        ]
        return JSONResponse(content={"folders": simplified})
    except Exception as e:
        return JSONResponse(
            status_code=502,
            content={"error": f"Could not reach Radarr: {e}"},
        )


class AddToRadarrRequest(BaseModel):
    folder_path: str


@router.post("/movies/{tmdb_id}/add")
async def add_movie_to_radarr(
    tmdb_id: int, body: AddToRadarrRequest
) -> JSONResponse:
    """
    Push a movie to Radarr using the chosen root folder.
    Returns JSON: {success, already_exists, message, radarr_id}
    """
    movie = await Movie.find_one(Movie.tmdb_id == tmdb_id)
    if not movie:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "Movie not found in local database."},
        )

    # Extract release year from release_date field
    year: Optional[int] = None
    if movie.release_date and movie.release_date != "TBA":
        try:
            year = int(movie.release_date[:4])
        except ValueError:
            pass

    try:
        result = await radarr_service.add_movie(
            tmdb_id=tmdb_id,
            title=movie.title,
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
                "message": f"Radarr error: {e}",
                "radarr_id": None,
            },
        )
