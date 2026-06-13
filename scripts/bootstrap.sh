#!/usr/bin/env bash
# Bootstrap local development: build, start, migrate, create admin.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "→ .env ausente; copiando de .env.example (preencha os segredos!)"
  cp .env.example .env
fi

echo "→ Subindo serviços (build)…"
docker compose up -d --build

echo "→ Aguardando banco…"
sleep 5

echo "→ Rodando migrações…"
docker compose exec -T web alembic upgrade head

echo "→ Criando usuário admin…"
docker compose exec -T web python scripts/create_admin.py

echo "✓ Pronto. Web em http://localhost:8060  (login em /login)"
