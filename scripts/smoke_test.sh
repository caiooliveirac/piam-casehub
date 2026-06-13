#!/usr/bin/env bash
# Smoke test: verify /health responds 200 with status ok.
set -euo pipefail

URL="${1:-http://localhost:8060}/health"
echo "→ GET ${URL}"

if curl -fsS "${URL}" | grep -q '"status":"ok"'; then
  echo "✓ Health OK"
  exit 0
else
  echo "✗ Health check falhou"
  exit 1
fi
