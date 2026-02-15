#!/usr/bin/env python3
"""
HTML generator for movie releases
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict

class HTMLGenerator:
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
    
    def generate_html(self, output_file: str = "releases.html"):
        """Generate HTML page with movie releases"""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Movie Releases - {datetime.now().strftime('%B %Y')}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 30px 0;
        }}
        
        h1 {{
            font-size: 3rem;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .subtitle {{
            font-size: 1.2rem;
            color: #b0b0b0;
        }}
        
        .controls {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}
        
        .btn {{
            padding: 12px 24px;
            background: rgba(255, 255, 255, 0.1);
            border: 2px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            color: #e0e0e0;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.3s ease;
        }}
        
        .btn:hover {{
            background: rgba(255, 255, 255, 0.2);
            border-color: #4ecdc4;
            transform: translateY(-2px);
        }}
        
        .btn.active {{
            background: #4ecdc4;
            border-color: #4ecdc4;
            color: #1a1a2e;
        }}
        
        .filter-section {{
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        
        .filter-btn {{
            padding: 8px 16px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            color: #b0b0b0;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.3s ease;
        }}
        
        .filter-btn:hover {{
            background: rgba(255, 255, 255, 0.1);
            color: #e0e0e0;
        }}
        
        .filter-btn.active {{
            background: #ff6b6b;
            border-color: #ff6b6b;
            color: white;
        }}
        
        .stats {{
            text-align: center;
            margin-bottom: 30px;
            font-size: 1.1rem;
            color: #4ecdc4;
        }}
        
        .grid-view {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 30px;
            margin-bottom: 40px;
        }}
        
        .list-view {{
            display: flex;
            flex-direction: column;
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .movie-card {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            overflow: hidden;
            transition: all 0.3s ease;
            cursor: pointer;
            border: 2px solid transparent;
        }}
        
        .movie-card:hover {{
            transform: translateY(-8px);
            border-color: #4ecdc4;
            box-shadow: 0 10px 30px rgba(78, 205, 196, 0.3);
        }}
        
        .poster-container {{
            position: relative;
            width: 100%;
            padding-top: 150%;
            background: #2a2a3e;
            overflow: hidden;
        }}
        
        .poster-container img {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        
        .no-poster {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 3rem;
            opacity: 0.3;
        }}
        
        .release-badge {{
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(255, 107, 107, 0.9);
            color: white;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: bold;
            text-transform: uppercase;
        }}
        
        .movie-info {{
            padding: 20px;
        }}
        
        .movie-title {{
            font-size: 1.3rem;
            font-weight: bold;
            margin-bottom: 8px;
            color: #ffffff;
        }}
        
        .movie-meta {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 10px;
            font-size: 0.9rem;
            color: #b0b0b0;
        }}
        
        .rating {{
            display: flex;
            align-items: center;
            gap: 5px;
            color: #ffd700;
        }}
        
        .genres {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-bottom: 12px;
        }}
        
        .genre-tag {{
            background: rgba(78, 205, 196, 0.2);
            color: #4ecdc4;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.8rem;
        }}
        
        .overview {{
            color: #b0b0b0;
            line-height: 1.6;
            margin-bottom: 15px;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        
        .cast {{
            margin-bottom: 15px;
        }}
        
        .cast-title {{
            font-size: 0.9rem;
            color: #4ecdc4;
            margin-bottom: 6px;
            font-weight: bold;
        }}
        
        .cast-list {{
            color: #b0b0b0;
            font-size: 0.85rem;
        }}
        
        .actions {{
            display: flex;
            gap: 10px;
        }}
        
        .action-btn {{
            flex: 1;
            padding: 10px;
            background: rgba(78, 205, 196, 0.1);
            border: 1px solid #4ecdc4;
            border-radius: 6px;
            color: #4ecdc4;
            text-decoration: none;
            text-align: center;
            font-size: 0.9rem;
            transition: all 0.3s ease;
        }}
        
        .action-btn:hover {{
            background: #4ecdc4;
            color: #1a1a2e;
        }}
        
        /* List view specific styles */
        .list-view .movie-card {{
            display: flex;
            flex-direction: row;
        }}
        
        .list-view .poster-container {{
            width: 200px;
            padding-top: 0;
            min-height: 300px;
            flex-shrink: 0;
        }}
        
        .list-view .movie-info {{
            flex: 1;
        }}
        
        .list-view .overview {{
            -webkit-line-clamp: 5;
        }}
        
        footer {{
            text-align: center;
            margin-top: 60px;
            padding: 20px;
            color: #b0b0b0;
            font-size: 0.9rem;
        }}
        
        .hidden {{
            display: none !important;
        }}
        
        @media (max-width: 768px) {{
            .list-view .movie-card {{
                flex-direction: column;
            }}
            
            .list-view .poster-container {{
                width: 100%;
                padding-top: 150%;
                min-height: 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎬 Movie Releases</h1>
            <p class="subtitle">{datetime.now().strftime('%B %Y')}</p>
        </header>
        
        <div class="controls">
            <button class="btn active" data-view="grid" onclick="toggleView('grid')">Grid View</button>
            <button class="btn" data-view="list" onclick="toggleView('list')">List View</button>
        </div>
        
        <div class="filter-section">
            <button class="filter-btn active" data-filter="all" onclick="filterByType('all')">All ({len(self.movies)})</button>
"""
        
        # Add filter buttons for each release type
        release_types = {}
        for movie in self.movies:
            rt = movie["release_type"]
            release_types[rt] = release_types.get(rt, 0) + 1
        
        for rt, count in sorted(release_types.items()):
            html += f'            <button class="filter-btn" data-filter="{rt}" onclick="filterByType(\'{rt}\')">{rt} ({count})</button>\n'
        
        html += """        </div>
        
        <div class="stats">
            <span id="movie-count"></span>
        </div>
        
        <div id="movie-container" class="grid-view">
"""
        
        # Add movie cards
        for movie in self.movies:
            poster_url = f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie["poster_path"] else ""
            trailer_link = movie["trailer_url"] if movie["trailer_url"] else "#"
            runtime_str = f"{movie['runtime']} min" if movie["runtime"] else "N/A"
            
            cast_text = ", ".join([c["name"] for c in movie["cast"][:3]]) if movie["cast"] else "Cast information not available"
            
            genres_html = "".join([f'<span class="genre-tag">{g}</span>' for g in movie["genres"]])
            
            html += f"""
            <div class="movie-card" data-type="{movie['release_type']}">
                <div class="poster-container">
                    {"<img src='" + poster_url + "' alt='" + movie['title'] + "' loading='lazy'>" if poster_url else "<div class='no-poster'>🎬</div>"}
                    <div class="release-badge">{movie['release_type']}</div>
                </div>
                <div class="movie-info">
                    <h2 class="movie-title">{movie['title']}</h2>
                    <div class="movie-meta">
                        <span class="rating">⭐ {movie['vote_average']:.1f}</span>
                        <span>📅 {movie['release_date']}</span>
                        <span>⏱️ {runtime_str}</span>
                    </div>
                    <div class="genres">
                        {genres_html}
                    </div>
                    <p class="overview">{movie['overview']}</p>
                    <div class="cast">
                        <div class="cast-title">Cast</div>
                        <div class="cast-list">{cast_text}</div>
                    </div>
                    <div class="actions">
                        <a href="{movie['tmdb_url']}" target="_blank" class="action-btn">TMDb</a>
                        {"<a href='" + trailer_link + "' target='_blank' class='action-btn'>Trailer</a>" if trailer_link != "#" else ""}
                    </div>
                </div>
            </div>
"""
        
        html += """        </div>
        
        <footer>
            <p>Data from The Movie Database (TMDb)</p>
            <p>Generated on """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
        </footer>
    </div>
    
    <script>
        function toggleView(view) {
            const container = document.getElementById('movie-container');
            const buttons = document.querySelectorAll('.btn[data-view]');
            
            buttons.forEach(btn => {
                if (btn.dataset.view === view) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });
            
            if (view === 'grid') {
                container.className = 'grid-view';
            } else {
                container.className = 'list-view';
            }
        }
        
        function filterByType(type) {
            const cards = document.querySelectorAll('.movie-card');
            const buttons = document.querySelectorAll('.filter-btn');
            let visibleCount = 0;
            
            buttons.forEach(btn => {
                if (btn.dataset.filter === type) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });
            
            cards.forEach(card => {
                if (type === 'all' || card.dataset.type === type) {
                    card.classList.remove('hidden');
                    visibleCount++;
                } else {
                    card.classList.add('hidden');
                }
            });
            
            updateCount(visibleCount);
        }
        
        function updateCount(count) {
            const countEl = document.getElementById('movie-count');
            countEl.textContent = `Showing ${count} movie${count !== 1 ? 's' : ''}`;
        }
        
        // Initialize
        window.addEventListener('load', () => {
            updateCount(document.querySelectorAll('.movie-card').length);
        });
    </script>
</body>
</html>
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"HTML generated: {output_file}")
        return output_file


def main():
    parser = argparse.ArgumentParser(description="Generate HTML page for movie releases")
    parser.add_argument("--file", default="releases.json", help="JSON data file")
    parser.add_argument("--output", default="releases.html", help="Output HTML file")
    
    args = parser.parse_args()
    
    generator = HTMLGenerator(args.file)
    generator.generate_html(args.output)


if __name__ == "__main__":
    main()