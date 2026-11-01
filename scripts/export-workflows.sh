#!/usr/bin/env bash
# Exporte tous les workflows de n8n vers ./workflows (un fichier JSON par workflow)
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose exec -T n8n n8n export:workflow --backup --output=/home/node/workflows/
echo "Workflows exportés dans ./workflows — pense à les committer."
