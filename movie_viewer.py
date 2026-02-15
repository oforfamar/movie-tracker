#!/usr/bin/env python3
"""
CLI viewer for movie releases
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict

class MovieCLI:
    def __init__(self, data_file: str = "releases.json"):
        self.data_file = data_file
        self.movies = self._load_data()
    
    def _load_data(self) -> List[Dict]:
        """Load movie data from JSON file"""
        if not Path(self.data_file).exists():
            print(f"Error: {self.data_file} not found. Run movie_tracker.py first.")
            return []
        
        with open(self.data_file, 'r') as f:
            return json.load(f)
    
    def display_compact(self):
        """Display compact list view"""
        if not self.movies:
            print("No movies found.")
            return
        
        print(f"\n{'='*80}")
        print(f"MOVIE RELEASES ({len(self.movies)} movies)")
        print(f"{'='*80}\n")
        
        for movie in self.movies:
            title = movie["title"]
            date = movie["release_date"]
            rating = movie["vote_average"]
            release_type = movie["release_type"]
            
            print(f"📅 {date} | ⭐ {rating:.1f}/10 | {release_type}")
            print(f"   {title}")
            
            if movie["genres"]:
                print(f"   Genres: {', '.join(movie['genres'])}")
            
            if movie["cast"]:
                cast_names = [c["name"] for c in movie["cast"][:3]]
                print(f"   Cast: {', '.join(cast_names)}")
            
            print()
    
    def display_detailed(self):
        """Display detailed view with descriptions"""
        if not self.movies:
            print("No movies found.")
            return
        
        print(f"\n{'='*80}")
        print(f"MOVIE RELEASES - DETAILED VIEW ({len(self.movies)} movies)")
        print(f"{'='*80}\n")
        
        for i, movie in enumerate(self.movies, 1):
            print(f"\n{i}. {movie['title']}")
            print(f"   {'─'*75}")
            print(f"   Release Date: {movie['release_date']}")
            print(f"   Type: {movie['release_type']}")
            print(f"   Rating: ⭐ {movie['vote_average']:.1f}/10 ({movie['vote_count']} votes)")
            
            if movie["runtime"]:
                print(f"   Runtime: {movie['runtime']} minutes")
            
            if movie["genres"]:
                print(f"   Genres: {', '.join(movie['genres'])}")
            
            print(f"\n   Description:")
            # Word wrap the overview
            words = movie["overview"].split()
            line = "   "
            for word in words:
                if len(line) + len(word) + 1 > 80:
                    print(line)
                    line = "   " + word
                else:
                    line += " " + word if line != "   " else word
            if line != "   ":
                print(line)
            
            if movie["cast"]:
                print(f"\n   Main Cast:")
                for actor in movie["cast"]:
                    print(f"     • {actor['name']} as {actor['character']}")
            
            if movie["trailer_url"]:
                print(f"\n   🎬 Trailer: {movie['trailer_url']}")
            
            print(f"   🔗 TMDb: {movie['tmdb_url']}")
            print()
    
    def display_by_type(self):
        """Display movies grouped by release type"""
        if not self.movies:
            print("No movies found.")
            return
        
        # Group by release type
        by_type = {}
        for movie in self.movies:
            release_type = movie["release_type"]
            if release_type not in by_type:
                by_type[release_type] = []
            by_type[release_type].append(movie)
        
        print(f"\n{'='*80}")
        print(f"MOVIE RELEASES BY TYPE")
        print(f"{'='*80}\n")
        
        for release_type, movies in sorted(by_type.items()):
            print(f"\n{release_type.upper()} ({len(movies)} movies)")
            print(f"{'-'*80}")
            
            for movie in movies:
                print(f"  • {movie['title']} ({movie['release_date']}) - ⭐ {movie['vote_average']:.1f}/10")
            print()
    
    def search(self, query: str):
        """Search movies by title"""
        query_lower = query.lower()
        results = [m for m in self.movies if query_lower in m["title"].lower()]
        
        if not results:
            print(f"No movies found matching '{query}'")
            return
        
        print(f"\nFound {len(results)} movie(s) matching '{query}':\n")
        for movie in results:
            print(f"• {movie['title']} ({movie['release_date']})")
            print(f"  {movie['overview'][:100]}...")
            if movie["trailer_url"]:
                print(f"  Trailer: {movie['trailer_url']}")
            print()


def main():
    parser = argparse.ArgumentParser(description="View movie releases")
    parser.add_argument("--file", default="releases.json", help="JSON data file")
    parser.add_argument("--view", choices=["compact", "detailed", "by-type"], 
                       default="compact", help="View mode")
    parser.add_argument("--search", help="Search for a movie by title")
    
    args = parser.parse_args()
    
    cli = MovieCLI(args.file)
    
    if args.search:
        cli.search(args.search)
    elif args.view == "compact":
        cli.display_compact()
    elif args.view == "detailed":
        cli.display_detailed()
    elif args.view == "by-type":
        cli.display_by_type()


if __name__ == "__main__":
    main()