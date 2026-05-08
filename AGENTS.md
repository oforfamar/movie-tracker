# AGENTS.md / CLAUDE.md

Guidelines for agentic coding agents working in this repository.
Both `AGENTS.md` and `CLAUDE.md` contain identical content — different agents
look for different filenames. Always keep them in sync.

---

## Project Overview

Movie Tracker is a Python 3.12 FastAPI web application that fetches upcoming movie
releases and TV series from the TMDb API, stores them in MongoDB, and presents
them as a Plex-style dark-themed UI. Users can filter, sort, push any movie to a
self-hosted Radarr instance, and push any TV series to a self-hosted Sonarr instance.

**Pipeline:**
```
APScheduler (daily)
  ├─ app/services/tmdb.py         →  MongoDB (movies collection)
  │                                    └─ app/routers/movies.py  →  Jinja2 templates  →  browser
  │                                    └─ app/routers/radarr.py  →  Radarr API
  └─ app/services/tmdb_series.py  →  MongoDB (series collection)
                                       └─ app/routers/series.py  →  Jinja2 templates  →  browser
                                       └─ app/routers/sonarr.py  →  Sonarr API
```

**External services:**
- TMDb REST API v3 (movie and TV series data)
- MongoDB (external cluster, auth required)
- Radarr (self-hosted, push movies for download)
- Sonarr (self-hosted, push TV series for download)

---

## Project Structure

```
movie-tracker/
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI app + lifespan (DB init, scheduler)
│   ├── config.py                 # Pydantic Settings — reads .env
│   ├── database.py               # Async PyMongo client + Beanie init
│   ├── models/
│   │   ├── movie.py              # Beanie Document + CastMember/WatchProvider embedded models
│   │   └── series.py             # Beanie Document for TV series
│   ├── routers/
│   │   ├── movies.py             # GET /movies, GET /movies/{tmdb_id}
│   │   ├── radarr.py             # GET /radarr/folders, POST /radarr/movies/{tmdb_id}/add
│   │   ├── series.py             # GET /series, GET /series/{tmdb_id}
│   │   └── sonarr.py             # GET /sonarr/folders, POST /sonarr/series/{tmdb_id}/add
│   ├── services/
│   │   ├── tmdb.py               # Async TMDb client, movie fetch + upsert logic
│   │   ├── tmdb_series.py        # Async TMDb client, series fetch + upsert logic
│   │   ├── radarr.py             # Async Radarr API client
│   │   └── sonarr.py             # Async Sonarr API client
│   ├── scheduler.py              # APScheduler daily_fetch job (movies + series)
│   └── templates/
│       ├── base.html             # Layout, Tailwind CDN, nav, Radarr + Sonarr modals
│       ├── index.html            # Movie card grid with filter/sort bar
│       ├── detail.html           # Single movie detail page
│       ├── 404.html              # Context-aware 404 (movie or series)
│       ├── partials/
│       │   └── movie_card.html   # Jinja2 macro — reusable movie card
│       └── series/
│           ├── index.html        # Series card grid with filter/sort bar
│           ├── detail.html       # Single series detail page
│           └── partials/
│               └── series_card.html  # Jinja2 macro — reusable series card
├── static/
│   └── js/
│       └── main.js               # Modal logic, fetch() POST, button state (Radarr + Sonarr)
├── systemd/
│   └── movie-tracker.service     # Copy to /etc/systemd/system/ on Debian/Ubuntu LXC
├── openrc/
│   └── movie-tracker             # Copy to /etc/init.d/ on Alpine LXC
├── .env                          # Never committed — real secrets
├── .env.example                  # Committed template
├── requirements.txt
├── AGENTS.md                     # This file
└── CLAUDE.md                     # Identical to AGENTS.md
```

---

## Commands

### Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run the development server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Trigger a manual TMDb fetch (app must be running)

```bash
curl -X POST http://localhost:8000/admin/fetch
```

### View logs in production (Debian/Ubuntu — systemd)

```bash
journalctl -u movie-tracker -f
```

### View logs in production (Alpine — OpenRC)

```bash
tail -f /var/log/movie-tracker.log
```

### No test suite

There is no test runner configured. Do not add one without explicit instruction.

### No linter

No linter or formatter is configured. Follow PEP 8 manually.
The `.gitignore` includes `.ruff_cache/` — `ruff` is the intended future choice.

---

## Environment Variables

All configuration is read from `.env` via Pydantic Settings (`app/config.py`).
Copy `.env.example` to `.env` and fill in real values before running.

| Variable | Description | Example |
|---|---|---|
| `TMDB_API_KEY` | TMDb v3 API key | `abc123` |
| `TMDB_REGIONS` | Comma-separated region codes | `US,GB` |
| `MONGODB_URI` | Full MongoDB connection URI with auth | `mongodb://user:pass@host:27017/movietracker?authSource=admin` |
| `RADARR_URL` | Radarr base URL (no trailing slash) | `http://192.168.1.10:7878` |
| `RADARR_API_KEY` | Radarr API key | `xyz789` |
| `RADARR_QUALITY_PROFILE` | Exact name of quality profile in Radarr | `4K-2160p` |
| `SONARR_URL` | Sonarr base URL (no trailing slash) | `http://192.168.1.10:8989` |
| `SONARR_API_KEY` | Sonarr API key | `xyz789` |
| `SONARR_QUALITY_PROFILE` | Exact name of quality profile in Sonarr | `WEB-1080p` |
| `FETCH_HOUR` | UTC hour (0-23) for daily auto-fetch | `3` |
| `PORT` | Uvicorn listen port | `8000` |

---

## Code Style

### General

- Python 3.12. All functions that perform I/O must be `async def`.
- Use `httpx.AsyncClient` for all outbound HTTP — never `requests`.
- Use `typing.List`, `typing.Dict`, `typing.Optional` (not bare `list[dict]` or `X | None`).
- Annotate every function parameter and return type.
- 4-space indentation, double quotes, max 88 characters per line.
- Two blank lines between top-level definitions, one between methods.

### Imports

Standard library first, then third-party. Separate groups with a blank line.
Alphabetical within each group.

```python
import asyncio
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from beanie import Document
from fastapi import APIRouter
```

### Naming

| Scope | Convention | Example |
|---|---|---|
| Files | `snake_case.py` | `tmdb.py`, `movie_card.html` |
| Classes | `PascalCase` | `Movie`, `CastMember` |
| Functions / methods | `snake_case` | `fetch_and_upsert`, `get_root_folders` |
| Private helpers | `_snake_case` | `_extract_cast`, `_get_genres` |
| Variables | `snake_case` | `all_stubs`, `quality_profile_id` |
| Constants / maps | `snake_case` dict | `RELEASE_TYPE_MAP` (module-level maps use `UPPER_SNAKE`) |
| CLI / env vars | `UPPER_SNAKE` | `TMDB_API_KEY` |
| Route path params | `snake_case` | `tmdb_id` |

### Error handling

Three patterns — do not introduce new ones.

**1. HTTP requests** — always call `raise_for_status()` immediately.

```python
response = await client.get(url, params=params)
response.raise_for_status()
```

**2. Per-item enrichment loops** — catch broadly, log, continue.

```python
try:
    details = await _fetch_movie_details(client, stub["id"])
except Exception as e:
    print(f"[TMDb] Error enriching '{stub.get('title')}': {e}")
    continue
```

**3. Route handlers** — catch exceptions from services, return `JSONResponse`
with an appropriate HTTP status code and `{"error": "..."}` body.

```python
try:
    folders = await radarr_service.get_root_folders()
except Exception as e:
    return JSONResponse(status_code=502, content={"error": str(e)})
```

All output goes to `print()`. Do not use the `logging` module.

---

## Data Model

### Movie (`app/models/movie.py`)

The canonical document for movies.
Upsert key: `tmdb_id` (unique index). Never duplicate — always upsert.

```python
class Movie(Document):
    tmdb_id: int
    title: str
    release_date: Optional[str]   # "YYYY-MM-DD" or "TBA"
    overview: str
    poster_path: Optional[str]    # e.g. "/abc123.jpg" — prepend image base URL in templates
    backdrop_path: Optional[str]
    vote_average: float
    vote_count: int
    runtime: Optional[int]        # minutes
    genres: List[str]             # resolved names
    cast: List[CastMember]        # top 5 billed, embedded
    trailer_url: Optional[str]    # YouTube URL or None
    release_type: str             # "Theatrical", "Digital", "TV/Streaming", etc.
    tmdb_url: str
    regions: List[str]            # accumulated, e.g. ["US", "GB"]
    fetched_at: datetime
```

### Series (`app/models/series.py`)

Mirrors Movie but for TV series. Separate `series` MongoDB collection.
Upsert key: `tmdb_id`. Reuses `CastMember` and `WatchProvider` from `movie.py`.

```python
class Series(Document):
    tmdb_id: int
    title: str
    first_air_date: Optional[str]    # "YYYY-MM-DD" or "TBA"
    overview: str
    poster_path: Optional[str]
    backdrop_path: Optional[str]
    vote_average: float
    vote_count: int
    number_of_seasons: Optional[int]
    number_of_episodes: Optional[int]
    status: str                      # "Returning Series", "Ended", "Cancelled", etc.
    genres: List[str]
    cast: List[CastMember]           # top 5 billed, embedded
    trailer_url: Optional[str]       # YouTube URL or None
    tmdb_url: str                    # https://www.themoviedb.org/tv/{id}
    regions: List[str]               # accumulated, e.g. ["US", "GB"]
    watch_providers: List[WatchProvider]
    fetched_at: datetime             # TTL index — docs expire 90 days after last fetch
```

Image URL construction (templates only):
```
https://image.tmdb.org/t/p/w500{poster_path}
https://image.tmdb.org/t/p/w1280{backdrop_path}
```

---

## Architecture Notes

### TMDb service (`app/services/tmdb.py`)

- `fetch_and_upsert(region, year, month)` — public entry point called by scheduler.
- Fetches up to 5 pages of `GET /discover/movie`, then enriches each stub with
  `GET /movie/{id}?append_to_response=credits,videos,release_dates`.
- Upserts by `tmdb_id`; merges `regions` list rather than overwriting.
- Auth: API key as query param `?api_key=...`, never in headers.

### TMDb series service (`app/services/tmdb_series.py`)

- `fetch_and_upsert(region, year, month)` — public entry point called by scheduler.
- Fetches up to 5 pages of `GET /discover/tv`, then enriches each stub with
  `GET /tv/{id}?append_to_response=aggregate_credits,videos,watch/providers,content_ratings`.
- Uses `aggregate_credits` (not `credits`) for TV cast — this is the correct TMDb endpoint.
- Upserts into the `series` collection by `tmdb_id`; merges `regions` list.
- Auth: API key as query param `?api_key=...`, never in headers.

### Radarr service (`app/services/radarr.py`)

- `get_root_folders()` — lists root folders from `GET /api/v3/rootfolder`.
- `add_movie(tmdb_id, title, year, folder_path)` — checks existence first via
  `GET /api/v3/movie`, resolves quality profile ID, then `POST /api/v3/movie`.
- Quality profile name comes from `settings.radarr_quality_profile` (`4K-2160p`).
- Auth: `X-Api-Key` header.

### Sonarr service (`app/services/sonarr.py`)

- `get_root_folders()` — lists root folders from `GET /api/v3/rootfolder`.
- `add_series(tmdb_id, title, year, folder_path)` — checks library via
  `GET /api/v3/series` (scans for matching `tmdbId`), looks up metadata via
  `GET /api/v3/series/lookup?term=tmdb:{id}`, then `POST /api/v3/series`.
- Quality profile name comes from `settings.sonarr_quality_profile` (`WEB-1080p`).
- Auth: `X-Api-Key` header.

### Scheduler (`app/scheduler.py`)

- `AsyncIOScheduler`, registered in `app/main.py` lifespan.
- `daily_fetch()` runs at `settings.fetch_hour:00 UTC`.
- Fetches current month + next month for each region in `settings.tmdb_regions`.
- Runs both movie and series fetches per region/month, with independent error handling.
- On first boot (empty DB), an immediate fetch is triggered via `asyncio.create_task`.

### Frontend (`app/templates/`)

- Permanent dark mode (`<html class="dark">`).
- Tailwind CSS via Play CDN — no build step, no `npm`.
- Custom `plex` colour (`#e5a00d`) defined in the inline Tailwind config in `base.html`.
- All filtering and sorting is server-side (MongoDB query params); no client-side
  data manipulation.
- `static/js/main.js` handles only: modal open/close, folder dropdown population
  via `fetch('/radarr/folders')` or `fetch('/sonarr/folders')`, POST to add
  movie/series, button state update.
- `navigateWithFilter()` targets `/movies`; `navigateSeriesWithFilter()` targets
  `/series` and uses `status` instead of `release_type` as a filter field.
- Do not add JS frameworks or build tooling.

### API routes

| Method | Path | Handler |
|---|---|---|
| `GET` | `/` | Redirect → `/movies` |
| `GET` | `/movies` | `routers/movies.py` — grid page |
| `GET` | `/movies/{tmdb_id}` | `routers/movies.py` — detail page |
| `GET` | `/radarr/folders` | `routers/radarr.py` — folder list JSON |
| `POST` | `/radarr/movies/{tmdb_id}/add` | `routers/radarr.py` — push to Radarr |
| `GET` | `/series` | `routers/series.py` — grid page |
| `GET` | `/series/{tmdb_id}` | `routers/series.py` — detail page |
| `GET` | `/sonarr/folders` | `routers/sonarr.py` — folder list JSON |
| `POST` | `/sonarr/series/{tmdb_id}/add` | `routers/sonarr.py` — push to Sonarr |
| `POST` | `/admin/fetch` | `main.py` — trigger manual fetch (movies + series) |

---

## Deployment (LXC)

### Debian/Ubuntu

```bash
# 1. Create user
useradd -r -s /bin/false movietracker

# 2. Clone and install
git clone <repo> /opt/movie-tracker
cd /opt/movie-tracker
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# 3. Configure
cp .env.example .env
nano .env          # fill in real values

# 4. Install systemd unit
cp systemd/movie-tracker.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable movie-tracker
systemctl start movie-tracker

# 5. Check logs
journalctl -u movie-tracker -f
```

### Alpine

```bash
# 1. Install Python
apk add python3 py3-pip git

# 2. Create user
adduser -S -H -s /sbin/nologin movietracker

# 3. Clone and install
git clone <repo> /opt/movie-tracker
cd /opt/movie-tracker
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# 4. Configure
cp .env.example .env
vi .env            # fill in real values

# 5. Install OpenRC service
cp openrc/movie-tracker /etc/init.d/movie-tracker
chmod +x /etc/init.d/movie-tracker
rc-update add movie-tracker default
rc-service movie-tracker start

# 6. Check logs
tail -f /var/log/movie-tracker.log
```

---

## Commit Convention

Conventional Commits. Include PR number when applicable.

```
feat: add genre filter to movie grid (#4)
fix: handle missing release_dates in TMDb enrichment (#5)
chore: update default fetch hour to 3 UTC (#6)
```

Common prefixes: `feat`, `fix`, `chore`, `refactor`, `docs`.
