# Movie Tracker

A self-hosted, Plex-style web application that fetches upcoming movie releases
and TV series from the TMDb API, stores them in MongoDB, and lets you push any
title directly to a Radarr or Sonarr instance for download.

## Features

- Plex-inspired dark UI with poster grid, filter bar, and detail pages for both movies and series
- Automatic daily fetch via APScheduler (current + next month, configurable regions)
- Movies: server-side filtering by genre, release type, and region; sorting by date, rating, or title
- Series: server-side filtering by genre, status, watch provider, and region; sorting by air date, rating, or title
- Per-movie "Add to Radarr" button with folder selection modal
- Per-series "Add to Sonarr" button with folder selection modal
- Manual refresh trigger via the "Refresh Now" nav button or `POST /admin/fetch`
- Deployable as a systemd service (Debian/Ubuntu LXC) or OpenRC service (Alpine LXC)

## Requirements

- Python 3.12+
- MongoDB (external cluster with auth, or local instance)
- TMDb API key (free at [themoviedb.org](https://www.themoviedb.org/settings/api))
- Radarr instance (optional — filtering and browsing work without it)
- Sonarr instance (optional — filtering and browsing work without it)

## Quick start

```bash
git clone <repo> movie-tracker
cd movie-tracker

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and fill in real values

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://localhost:8000` — the app redirects to `/movies`. A `/series` section
is also available. On first boot with an empty database an initial fetch runs
automatically in the background.

## Configuration

All settings are read from `.env` (see `.env.example`):

| Variable | Description | Example |
|---|---|---|
| `TMDB_API_KEY` | TMDb v3 API key | `abc123` |
| `TMDB_REGIONS` | Comma-separated region codes | `US,GB` |
| `MONGODB_URI` | Full MongoDB connection URI | `mongodb://user:pass@host:27017/movietracker?authSource=admin` |
| `RADARR_URL` | Radarr base URL (no trailing slash) | `http://192.168.1.10:7878` |
| `RADARR_API_KEY` | Radarr API key | `xyz789` |
| `RADARR_QUALITY_PROFILE` | Quality profile name in Radarr | `4K-2160p` |
| `SONARR_URL` | Sonarr base URL (no trailing slash) | `http://192.168.1.10:8989` |
| `SONARR_API_KEY` | Sonarr API key | `xyz789` |
| `SONARR_QUALITY_PROFILE` | Quality profile name in Sonarr | `WEB-1080p` |
| `FETCH_HOUR` | UTC hour for the daily auto-fetch (0–23) | `3` |
| `PORT` | Uvicorn listen port | `8000` |

## Project structure

```
app/
├── main.py          # FastAPI app + lifespan (DB init, scheduler)
├── config.py        # Pydantic Settings — reads .env
├── database.py      # Async PyMongo client + Beanie init
├── scheduler.py     # APScheduler daily_fetch job (movies + series)
├── models/
│   ├── movie.py     # Beanie Document + CastMember/WatchProvider embedded models
│   └── series.py    # Beanie Document for TV series
├── routers/
│   ├── movies.py    # GET /movies, GET /movies/{tmdb_id}
│   ├── radarr.py    # GET /radarr/folders, POST /radarr/movies/{tmdb_id}/add
│   ├── series.py    # GET /series, GET /series/{tmdb_id}
│   └── sonarr.py    # GET /sonarr/folders, POST /sonarr/series/{tmdb_id}/add
├── services/
│   ├── tmdb.py      # Async TMDb client, movie fetch + upsert logic
│   ├── tmdb_series.py  # Async TMDb client, series fetch + upsert logic
│   ├── radarr.py    # Async Radarr API client
│   └── sonarr.py    # Async Sonarr API client
└── templates/       # Jinja2 templates (Tailwind via Play CDN)
    ├── index.html / detail.html / partials/  # Movies
    └── series/                               # Series (index, detail, partials)
static/js/main.js    # Modal, folder fetch, button state (Radarr + Sonarr)
systemd/             # systemd service unit (Debian/Ubuntu LXC)
openrc/              # OpenRC init script (Alpine LXC)
```

## API routes

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Redirect → `/movies` |
| `GET` | `/movies` | Movie grid with filter/sort |
| `GET` | `/movies/{tmdb_id}` | Movie detail page |
| `GET` | `/radarr/folders` | List Radarr root folders (JSON) |
| `POST` | `/radarr/movies/{tmdb_id}/add` | Push movie to Radarr |
| `GET` | `/series` | Series grid with filter/sort |
| `GET` | `/series/{tmdb_id}` | Series detail page |
| `GET` | `/sonarr/folders` | List Sonarr root folders (JSON) |
| `POST` | `/sonarr/series/{tmdb_id}/add` | Push series to Sonarr |
| `POST` | `/admin/fetch` | Trigger a manual TMDb fetch (movies + series) |

## Production deployment (LXC)

### Debian/Ubuntu

```bash
# 1. Create a dedicated user
useradd -r -s /bin/false movietracker

# 2. Clone and install
git clone <repo> /opt/movie-tracker
cd /opt/movie-tracker
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# 3. Configure
cp .env.example .env
nano .env

# 4. Install and start the systemd unit
cp systemd/movie-tracker.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now movie-tracker

# 5. Watch logs
journalctl -u movie-tracker -f
```

### Alpine

```bash
# 1. Install Python
apk add python3 py3-pip git

# 2. Create a dedicated user
adduser -S -H -s /sbin/nologin movietracker

# 3. Clone and install
git clone <repo> /opt/movie-tracker
cd /opt/movie-tracker
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# 4. Configure
cp .env.example .env
vi .env

# 5. Install and start the OpenRC service
cp openrc/movie-tracker /etc/init.d/movie-tracker
chmod +x /etc/init.d/movie-tracker
rc-update add movie-tracker default
rc-service movie-tracker start

# 6. Watch logs
tail -f /var/log/movie-tracker.log
```

## Credits

Movie data provided by [The Movie Database (TMDb)](https://www.themoviedb.org).
This product uses the TMDb API but is not endorsed or certified by TMDb.
