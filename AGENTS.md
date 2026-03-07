# AGENTS.md

Guidelines for agentic coding agents working in this repository.

---

## Project Overview

Movie Release Tracker is a plain Python 3.12 CLI tool that fetches upcoming movie
release data from the TMDb API and renders it as a terminal view or a static HTML
page. There is no web framework, no build system, and no test suite.

**Pipeline:**
```
movie_tracker.py  -->  releases.json  -->  generate_html.py  -->  releases.html
                                      -->  movie_viewer.py   -->  stdout
```

**Single external dependency:** `requests`

**Runtime config:** `config.json` (auto-created on first run, not committed)

**Data cache:** `releases.json` (generated output, not committed)

---

## Commands

### Setup

```bash
pip install requests
```

No virtual-environment tooling is configured. Use one if you prefer, but it is not
required by the project.

### Fetch movie data

```bash
python3 movie_tracker.py --api-key YOUR_KEY
python3 movie_tracker.py --api-key YOUR_KEY --month 3 --year 2026
python3 movie_tracker.py --api-key YOUR_KEY --output custom.json
```

### View data in the terminal

```bash
python3 movie_viewer.py                         # compact view (default)
python3 movie_viewer.py --view detailed
python3 movie_viewer.py --view by-type
python3 movie_viewer.py --search "title"
python3 movie_viewer.py --file custom.json
```

### Generate HTML report

```bash
python3 generate_html.py
python3 generate_html.py --file custom.json --output custom.html
```

### All-in-one convenience wrapper

```bash
./run.sh YOUR_API_KEY               # current month
./run.sh YOUR_API_KEY 3 2026        # March 2026
```

### Linting / formatting

No linter or formatter is currently configured. The `.gitignore` includes
`.ruff_cache/`, so `ruff` is the intended choice if one is added. Until then,
follow PEP 8 manually.

### Tests

There is no test suite. No test runner is installed or configured.

---

## Code Style

### Imports

- Group order: standard library, then third-party (`requests`). Separate groups
  with a blank line.
- No relative imports — all modules are at the package root.
- Use the legacy `typing` module forms: `List`, `Dict`, `Optional` (not the
  built-in `list[dict]` generics available since Python 3.9).
- Import only what is used. Keep imports alphabetical within each group.

```python
# correct
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

import requests
```

### Formatting

- 4-space indentation, no tabs.
- Two blank lines between top-level definitions (classes, `main`).
- One blank line between methods inside a class.
- Maximum line length: 88 characters (PEP 8 / Black default), enforced manually.
- Strings: use double quotes consistently.

### Type annotations

- Annotate every function parameter and return type.
- Use `typing.List[Dict]`, `typing.Dict`, `typing.Optional` — not bare `list`,
  `dict`, or `X | None` syntax.
- Data is passed as plain `dict` throughout. Do not introduce dataclasses,
  `TypedDict`, or Pydantic models.

```python
def filter_movies(self, movies: List[Dict]) -> List[Dict]:
def save_data(self, movies: List[Dict], filename: str = "releases.json"):
def _load_config(self) -> Dict:
```

### Naming conventions

| Scope | Convention | Example |
|---|---|---|
| Files | `snake_case.py` | `movie_tracker.py` |
| Classes | `PascalCase` | `MovieTracker` |
| Public methods / functions | `snake_case` | `fetch_releases` |
| Private methods | `_snake_case` | `_load_config` |
| Variables | `snake_case` | `all_movies`, `cast_names` |
| Local lookup maps | `snake_case` dict | `release_type_map` |
| CLI arguments | `--kebab-case` | `--api-key`, `--by-type` |

One class per file. No module-level constants in `ALL_CAPS` (not used in this
codebase).

### Error handling

Three patterns are used — stick to these; do not introduce new patterns or custom
exception classes.

**1. HTTP requests** — always call `raise_for_status()` immediately after every
`requests.get()`. Let the `requests.HTTPError` propagate.

```python
response = requests.get(url, params=params)
response.raise_for_status()
```

**2. Per-item enrichment loops** — catch broadly, log to stdout, and continue.

```python
try:
    details = self.get_movie_details(movie["id"])
    # ...
except Exception as e:
    print(f"Error fetching details for {movie['title']}: {e}")
    continue
```

**3. File access** — guard with `Path.exists()` before opening; print a
user-facing error and return an empty list.

```python
if not Path(self.data_file).exists():
    print(f"Error: {self.data_file} not found. Run movie_tracker.py first.")
    return []
```

All output — including errors — goes to `print()`. Do not use the `logging`
module.

### Module structure

Every `.py` file follows this exact layout:

```
1. Shebang:          #!/usr/bin/env python3
2. Module docstring
3. Imports
4. One class definition
5. def main():
6. if __name__ == "__main__": main()
```

Inside every class:
- `__init__` loads all state eagerly (config, data file).
- Private helpers (`_name`) come before public methods.
- No `@staticmethod`, no `@classmethod`, no `@property`.
- All state is held on `self`.

---

## Data Schema

The canonical in-memory / on-disk format is the enriched movie dict produced by
`MovieTracker.enrich_movie_data()` and stored in `releases.json`:

```python
{
    "id":           int,            # TMDb movie ID
    "title":        str,
    "release_date": str,            # "YYYY-MM-DD" or "TBA"
    "overview":     str,
    "poster_path":  str | None,     # e.g. "/abc123.jpg"
    "backdrop_path":str | None,
    "vote_average": float,
    "vote_count":   int,
    "runtime":      int | None,     # minutes
    "genres":       List[str],      # resolved names, e.g. ["Action", "Drama"]
    "cast":         List[{          # top 5 billed actors
                        "name": str,
                        "character": str
                    }],
    "trailer_url":  str | None,     # YouTube URL or None
    "release_type": str,            # "Theatrical", "Digital", "TV/Streaming", etc.
    "tmdb_url":     str,            # https://www.themoviedb.org/movie/{id}
}
```

`config.json` schema:

```json
{
    "region":              "US",
    "include_theatrical":  true,
    "include_streaming":   true,
    "genres_to_exclude":   [],
    "min_vote_average":    0.0,
    "languages":           ["en"]
}
```

---

## Architecture Notes

### TMDb API

- Base URL: `https://api.themoviedb.org/3`
- Auth: API key as a query parameter (`?api_key=...`), not in headers.
- All calls are synchronous, blocking `requests.get()`. No async, no threading.
- Pagination: manual `while True` loop; hard ceiling of 5 pages per query.
- Image URLs: `https://image.tmdb.org/t/p/w500{poster_path}`
- Trailer URLs: YouTube only — `type == "Trailer"` and `site == "YouTube"`.

### Generated HTML

`releases.html` is a self-contained static file with inline CSS and vanilla
JavaScript (no libraries). It is not a framework component and is regenerated
from scratch on every `generate_html.py` run.

---

## Commit Convention

This project uses Conventional Commits. Include the PR number when applicable.

```
feat: add genre filter to CLI viewer (#4)
fix: handle missing release_dates in enrichment (#5)
chore: update default config region to GB (#6)
```

Common prefixes: `feat`, `fix`, `chore`, `refactor`, `docs`.
