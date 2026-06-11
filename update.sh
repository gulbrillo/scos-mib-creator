#!/usr/bin/env bash
# Update the SCOS MIB Creator deployment:
# pull the latest code from GitHub, rebuild the images and restart the stack.
# Project data is kept (it lives in the named Docker volume "dbdata").
#
# Usage: ./update.sh
set -euo pipefail
cd "$(dirname "$0")"

echo "==> Pulling latest code"
git pull --ff-only

echo "==> Rebuilding and restarting containers"
docker compose up -d --build

echo "==> Cleaning up dangling images"
docker image prune -f >/dev/null

echo "==> Status"
docker compose ps

echo "==> Waiting for the application to come up"
for i in $(seq 1 30); do
    if curl -fsS http://localhost:8082/api/health >/dev/null 2>&1; then
        echo "OK — http://localhost:8082 is healthy."
        exit 0
    fi
    sleep 2
done
echo "WARNING: application did not report healthy within 60 s — check: docker compose logs web" >&2
exit 1
