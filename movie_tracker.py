#!/usr/bin/env python3
"""
Movie Release Tracker
Fetches upcoming movie releases from TMDb API and generates views
"""

import requests
import json
from datetime import datetime, timedelta
from pathlib import Path
import argparse
from typing import List, Dict, Optional

class MovieTracker:
    def __init__(self, api_key: str, config_path: str = "config.json"):
        self.api_key = api_key
        self.base_url = "https://api.themoviedb.org/3"
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """Load configuration from file or create default"""
        default_config = {
            "region": "US",  # Change to your region (e.g., "GB", "RO", etc.)
            "include_theatrical": True,
            "include_streaming": True,
            "genres_to_exclude": [],  # List of genre IDs to exclude
            "min_vote_average": 0.0,  # Minimum rating threshold
            "languages": ["en"],  # Preferred languages
        }
        
        if Path(self.config_path).exists():
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                # Merge with defaults
                return {**default_config, **config}
        else:
            # Save default config
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config
    
    def get_genres(self) -> Dict[int, str]:
        """Fetch genre mapping from TMDb"""
        url = f"{self.base_url}/genre/movie/list"
        params = {"api_key": self.api_key}
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        genres = {}
        for genre in response.json()["genres"]:
            genres[genre["id"]] = genre["name"]
        return genres
    
    def fetch_releases(self, start_date: str, end_date: str) -> List[Dict]:
        """Fetch movie releases between two dates"""
        url = f"{self.base_url}/discover/movie"
        
        params = {
            "api_key": self.api_key,
            "region": self.config["region"],
            "release_date.gte": start_date,
            "release_date.lte": end_date,
            "sort_by": "release_date.asc",
            "with_release_type": "2|3|4|5|6",  # Theatrical, Streaming, Digital, Physical, TV
        }
        
        all_movies = []
        page = 1
        
        while True:
            params["page"] = page
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            all_movies.extend(data["results"])
            
            if page >= data["total_pages"] or page >= 5:  # Limit to 5 pages max
                break
            page += 1
        
        return all_movies
    
    def get_movie_details(self, movie_id: int) -> Dict:
        """Get detailed information about a movie including cast and videos"""
        url = f"{self.base_url}/movie/{movie_id}"
        params = {
            "api_key": self.api_key,
            "append_to_response": "credits,videos,release_dates"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def filter_movies(self, movies: List[Dict]) -> List[Dict]:
        """Apply filters based on configuration"""
        filtered = []
        
        for movie in movies:
            # Filter by excluded genres
            if self.config["genres_to_exclude"]:
                if any(g in self.config["genres_to_exclude"] for g in movie.get("genre_ids", [])):
                    continue
            
            # Filter by minimum vote average
            if movie.get("vote_average", 0) < self.config["min_vote_average"]:
                continue
            
            filtered.append(movie)
        
        return filtered
    
    def enrich_movie_data(self, movies: List[Dict]) -> List[Dict]:
        """Enrich basic movie data with details, cast, and trailers"""
        enriched = []
        genres_map = self.get_genres()
        
        for i, movie in enumerate(movies):
            print(f"Fetching details for movie {i+1}/{len(movies)}: {movie['title']}")
            
            try:
                details = self.get_movie_details(movie["id"])
                
                # Get main cast (top 5)
                cast = []
                if "credits" in details and "cast" in details["credits"]:
                    cast = [
                        {"name": actor["name"], "character": actor["character"]}
                        for actor in details["credits"]["cast"][:5]
                    ]
                
                # Get YouTube trailer
                trailer_url = None
                if "videos" in details and "results" in details["videos"]:
                    trailers = [v for v in details["videos"]["results"] 
                               if v["type"] == "Trailer" and v["site"] == "YouTube"]
                    if trailers:
                        trailer_url = f"https://www.youtube.com/watch?v={trailers[0]['key']}"
                
                # Get release type for this region
                release_type = "Unknown"
                if "release_dates" in details:
                    for rd in details["release_dates"]["results"]:
                        if rd["iso_3166_1"] == self.config["region"]:
                            if rd["release_dates"]:
                                rt = rd["release_dates"][0]["type"]
                                release_type_map = {
                                    1: "Premiere",
                                    2: "Theatrical (Limited)",
                                    3: "Theatrical",
                                    4: "Digital",
                                    5: "Physical",
                                    6: "TV/Streaming"
                                }
                                release_type = release_type_map.get(rt, "Unknown")
                            break
                
                enriched_movie = {
                    "id": movie["id"],
                    "title": details["title"],
                    "release_date": movie.get("release_date", "TBA"),
                    "overview": details.get("overview", "No description available."),
                    "poster_path": movie.get("poster_path"),
                    "backdrop_path": movie.get("backdrop_path"),
                    "vote_average": details.get("vote_average", 0),
                    "vote_count": details.get("vote_count", 0),
                    "runtime": details.get("runtime"),
                    "genres": [genres_map.get(g["id"], g["name"]) for g in details.get("genres", [])],
                    "cast": cast,
                    "trailer_url": trailer_url,
                    "release_type": release_type,
                    "tmdb_url": f"https://www.themoviedb.org/movie/{movie['id']}"
                }
                
                enriched.append(enriched_movie)
                
            except Exception as e:
                print(f"Error fetching details for {movie['title']}: {e}")
                continue
        
        return enriched
    
    def get_monthly_releases(self, year: int, month: int) -> List[Dict]:
        """Get all releases for a specific month"""
        # Calculate start and end dates for the month
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        print(f"Fetching releases from {start_str} to {end_str}...")
        movies = self.fetch_releases(start_str, end_str)
        print(f"Found {len(movies)} movies")
        
        print("Applying filters...")
        movies = self.filter_movies(movies)
        print(f"{len(movies)} movies after filtering")
        
        print("Enriching movie data with cast and trailers...")
        enriched = self.enrich_movie_data(movies)
        
        return enriched
    
    def save_data(self, movies: List[Dict], filename: str = "releases.json"):
        """Save movie data to JSON file"""
        with open(filename, 'w') as f:
            json.dump(movies, f, indent=2)
        print(f"Saved data to {filename}")


def main():
    parser = argparse.ArgumentParser(description="Movie Release Tracker")
    parser.add_argument("--api-key", required=True, help="TMDb API key")
    parser.add_argument("--month", type=int, help="Month (1-12), defaults to current month")
    parser.add_argument("--year", type=int, help="Year, defaults to current year")
    parser.add_argument("--output", default="releases.json", help="Output JSON file")
    
    args = parser.parse_args()
    
    # Default to current month if not specified
    now = datetime.now()
    month = args.month or now.month
    year = args.year or now.year
    
    tracker = MovieTracker(args.api_key)
    movies = tracker.get_monthly_releases(year, month)
    tracker.save_data(movies, args.output)
    
    print(f"\nFetched {len(movies)} movies for {year}-{month:02d}")
    print(f"Data saved to {args.output}")


if __name__ == "__main__":
    main()