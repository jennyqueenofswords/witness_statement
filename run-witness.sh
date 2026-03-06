#!/bin/bash
# Local runner for Witness Statement — daily poems from the news
# Loads .env, generates poems, commits to main, rebuilds site, pushes to gh-pages

set -euo pipefail
cd "$(dirname "$0")"

# Load API keys
set -a
source .env
set +a

# Generate
python3 generate_poems.py

# Commit to main if there's anything new
git add _posts/
DATE=$(date -u +%Y-%m-%d)
if git diff --cached --quiet; then
    echo "[witness] nothing new"
    exit 0
fi

git commit -m "witness: $DATE"
git push origin main
echo "[witness] pushed $DATE to main"

# Rebuild static site and push to gh-pages
python3 build.py
git checkout gh-pages
cp _site/index.html index.html
git add index.html
git commit -m "rebuild: $DATE"
git push origin gh-pages
git checkout main
echo "[witness] site rebuilt and pushed to gh-pages"
