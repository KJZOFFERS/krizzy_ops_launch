#!/usr/bin/env bash
set -euo pipefail
echo "[1/2] Discord"
curl -sS -X POST "$DISCORD_WEBHOOK_OPS" -H 'Content-Type: application/json' \
  -d '{"content":"KRIZZY OPS Launch Test ✅"}' | cat
echo
echo "[2/2] SAM.gov"
curl -sS "$SAM_SEARCH_API" | head -c 300 | tr '\n' ' ' | cat
echo
