#!/bin/bash

# Movie Release Tracker - Quick Start Script
# Usage: ./run.sh YOUR_API_KEY [month] [year]

if [ -z "$1" ]; then
    echo "Usage: ./run.sh YOUR_API_KEY [month] [year]"
    echo ""
    echo "Examples:"
    echo "  ./run.sh abc123                    # Current month"
    echo "  ./run.sh abc123 3 2026            # March 2026"
    exit 1
fi

API_KEY=$1
MONTH=${2:-}
YEAR=${3:-}

echo "🎬 Movie Release Tracker"
echo "========================"
echo ""

# Build command
CMD="python3 movie_tracker.py --api-key $API_KEY"
if [ ! -z "$MONTH" ]; then
    CMD="$CMD --month $MONTH"
fi
if [ ! -z "$YEAR" ]; then
    CMD="$CMD --year $YEAR"
fi

# Fetch data
echo "📡 Fetching movie data..."
eval $CMD

if [ $? -ne 0 ]; then
    echo "❌ Failed to fetch movie data"
    exit 1
fi

echo ""
echo "✅ Data fetched successfully!"
echo ""

# Generate HTML
echo "🎨 Generating HTML page..."
python3 generate_html.py

if [ $? -ne 0 ]; then
    echo "❌ Failed to generate HTML"
    exit 1
fi

echo ""
echo "✅ All done!"
echo ""
echo "📊 Quick stats:"
python3 -c "import json; data = json.load(open('releases.json')); print(f'  Total movies: {len(data)}'); types = {}; [types.update({m['release_type']: types.get(m['release_type'], 0) + 1}) for m in data]; [print(f'  {k}: {v}') for k, v in sorted(types.items())]"
echo ""
echo "🌐 Open releases.html in your browser to view!"
echo "💻 Or run: python3 movie_viewer.py --view compact"