#!/usr/bin/env bash
# Importe dans n8n tous les workflows JSON présents dans ./workflows
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose exec -T n8n n8n import:workflow --separate --input=/home/node/workflows/
echo "Workflows importés. Rafraîchis l'éditeur n8n."
