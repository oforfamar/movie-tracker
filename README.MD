# Movie Release Tracker

A simple, flexible system to track movie releases from TMDb including theatrical and streaming releases.

## Features

- 🎬 Fetches movie releases from TMDb API
- 📅 Monthly digest (configurable for any time range)
- 🎨 Beautiful HTML page with poster grid view and list view
- 💻 CLI text viewer for quick scanning
- 🎯 Configurable filters (genres, ratings, release types)
- 🎭 Includes cast, trailers, and detailed info

## Setup

### 1. Get a TMDb API Key

1. Go to https://www.themoviedb.org/
2. Create a free account
3. Go to Settings → API → Create API Key
4. Choose "Developer" and fill out the form
5. Copy your API key (v3 auth)

### 2. Install Dependencies

```bash
pip install requests
```

That's it! The system uses only Python's standard library plus `requests`.

### 3. Configure (Optional)

On first run, a `config.json` file will be created with defaults:

```json
{
  "region": "US",
  "include_theatrical": true,
  "include_streaming": true,
  "genres_to_exclude": [],
  "min_vote_average": 0.0,
  "languages": ["en"]
}
```

**Configuration options:**

- `region`: Your region code (e.g., "US", "GB", "RO", "FR")
- `include_theatrical`: Include theatrical releases
- `include_streaming`: Include streaming/digital releases
- `genres_to_exclude`: List of genre IDs to filter out (see genre IDs below)
- `min_vote_average`: Minimum rating (0.0 to 10.0)
- `languages`: Preferred languages (e.g., ["en", "ro"])

**Genre IDs reference:**
- 28: Action
- 12: Adventure
- 16: Animation
- 35: Comedy
- 80: Crime
- 99: Documentary
- 18: Drama
- 10751: Family
- 14: Fantasy
- 36: History
- 27: Horror
- 10402: Music
- 9648: Mystery
- 10749: Romance
- 878: Science Fiction
- 10770: TV Movie
- 53: Thriller
- 10752: War
- 37: Western

## Usage

### Step 1: Fetch Movie Data

Fetch releases for the current month:

```bash
python movie_tracker.py --api-key YOUR_API_KEY
```

Fetch releases for a specific month:

```bash
python movie_tracker.py --api-key YOUR_API_KEY --month 3 --year 2026
```

This creates a `releases.json` file with all the data.

### Step 2: View the Data

**Option A: HTML Page (Recommended)**

```bash
python generate_html.py
```

Then open `releases.html` in your browser. Features:
- Toggle between grid and list views
- Filter by release type (Theatrical, Streaming, etc.)
- Click on posters for more info
- Direct links to trailers and TMDb pages

**Option B: CLI Viewer**

Compact view:
```bash
python movie_viewer.py --view compact
```

Detailed view with descriptions:
```bash
python movie_viewer.py --view detailed
```

Grouped by release type:
```bash
python movie_viewer.py --view by-type
```

Search for a specific movie:
```bash
python movie_viewer.py --search "batman"
```

## Examples

### Monthly digest workflow

```bash
# Fetch current month's releases
python movie_tracker.py --api-key YOUR_API_KEY

# Generate HTML page
python generate_html.py

# Or view in terminal
python movie_viewer.py --view compact
```

### Filter out horror and exclude low-rated movies

Edit `config.json`:
```json
{
  "region": "US",
  "genres_to_exclude": [27],
  "min_vote_average": 6.0
}
```

Then run the tracker again.

### Check upcoming releases

```bash
# Next month
python movie_tracker.py --api-key YOUR_API_KEY --month 3 --year 2026

# Generate HTML
python generate_html.py --output march_2026.html
```

## Automation

### Linux/Mac Cron Job

Add to your crontab to run on the 1st of each month:

```bash
0 0 1 * * cd /path/to/movie-tracker && python movie_tracker.py --api-key YOUR_API_KEY && python generate_html.py
```

### Windows Task Scheduler

Create a batch file `update_movies.bat`:

```batch
@echo off
cd C:\path\to\movie-tracker
python movie_tracker.py --api-key YOUR_API_KEY
python generate_html.py
```

Then schedule it in Task Scheduler.

## File Structure

```
movie-tracker/
├── movie_tracker.py    # Main fetcher script
├── movie_viewer.py     # CLI viewer
├── generate_html.py    # HTML generator
├── config.json         # Configuration (auto-created)
├── releases.json       # Data file (created by tracker)
├── releases.html       # HTML page (created by generator)
└── README.md
```

## Extending the System

### Add more filters

Edit the `filter_movies()` method in `movie_tracker.py`. For example, to exclude movies with specific keywords:

```python
def filter_movies(self, movies: List[Dict]) -> List[Dict]:
    filtered = []
    exclude_keywords = ["superhero", "marvel", "dc"]
    
    for movie in movies:
        # Your existing filters...
        
        # New keyword filter
        if any(kw in movie.get("title", "").lower() for kw in exclude_keywords):
            continue
        
        filtered.append(movie)
    
    return filtered
```

### Change the time range

Instead of monthly, you can fetch any date range by modifying the `fetch_releases()` call:

```python
movies = tracker.fetch_releases("2026-03-01", "2026-03-31")
```

### Add streaming service detection

TMDb doesn't directly tell you which streaming service a movie is on, but you can use their "watch providers" endpoint (you'd need to add this to the API calls).

## Tips

- **API Rate Limits**: The free tier is very generous (50 req/sec). The script is already optimized.
- **Poster Quality**: Change `w500` to `original` in `generate_html.py` for higher quality posters
- **Dark Theme**: The HTML uses a dark theme by default. Easy to customize in the `<style>` section.
- **Search**: Use TMDb's search if you want to find specific movies outside the date range

## Troubleshooting

**"No movies found"**: Check your region code and date range. Some regions have fewer releases.

**API errors**: Make sure your API key is correct and you haven't exceeded rate limits.

**Missing posters**: Some movies don't have poster images yet. They'll show a 🎬 icon instead.

## Contributing

Feel free to extend this! Some ideas:
- Add filtering by streaming service
- Create a web server version
- Add email/SMS notifications
- Integration with Plex/Jellyfin
- Add movie recommendations based on your preferences

## License

Do whatever you want with this code. It's yours now.

## Credits

Movie data provided by TMDb (The Movie Database).
This product uses the TMDb API but is not endorsed or certified by TMDb.
