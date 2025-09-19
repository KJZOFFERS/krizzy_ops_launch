#!/usr/bin/env bash
set -euo pipefail
BASE="${N8N_BASE_URL%/}"
HDR="x-n8n-api-key: $N8N_API_KEY"
curl -sS -H "$HDR" "$BASE/rest/workflows" | jq '.data[]|{id,name}'
