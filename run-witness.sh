#!/bin/bash
# Local runner for Witness Statement — daily poems from the news
# Loads .env, generates poems, commits and pushes

set -euo pipefail
cd "$(dirname "$0")"

# Load API keys
set -a
source .env
set +a

# Generate
python3 generate_poems.py

# Commit and push if there's anything new
git add _posts/
DATE=$(date -u +%Y-%m-%d)
if ! git diff --cached --quiet; then
    git commit -m "witness: $DATE"
    git push origin main
    echo "[witness] pushed $DATE"
else
    echo "[witness] nothing new"
fi
