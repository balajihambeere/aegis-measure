#!/usr/bin/env bash
# Brings the stack up and replays a realistic set of incidents through it.
# See scripts/seed_demo.py for what this actually does and why.
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
    echo "No .env found — copying .env.example. Add your ANTHROPIC_API_KEY to it" \
         "for the LLM-graded run step to actually succeed." >&2
    cp .env.example .env
fi

cd infrastructure
docker compose up -d --build
echo "Waiting for the API to become healthy..."
until curl -sf http://localhost:8001/health > /dev/null; do sleep 1; done
cd ..

python3 scripts/seed_demo.py
