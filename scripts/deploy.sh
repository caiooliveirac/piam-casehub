#!/usr/bin/env bash
# Idempotent deploy to the AWS instance over SSH.
#
# Reads deploy target from the environment (or .env):
#   DEPLOY_HOST, DEPLOY_USER, DEPLOY_PATH, DEPLOY_SSH_KEY
#
# It NEVER invents credentials. If the target is not configured it stops with
# a clear message after running local checks, so you can finish manually.
set -euo pipefail
cd "$(dirname "$0")/.."

MAIN_BRANCH="${MAIN_BRANCH:-main}"

# Load .env if present (without exporting secrets to logs).
if [ -f .env ]; then
  set -a; . ./.env; set +a
fi

echo "==> 1. Verificando branch principal"
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [ "${CURRENT_BRANCH}" != "${MAIN_BRANCH}" ]; then
  echo "✗ Você está em '${CURRENT_BRANCH}', esperado '${MAIN_BRANCH}'." >&2
  exit 1
fi

echo "==> 2. Rodando testes"
if command -v pytest >/dev/null 2>&1; then
  pytest -q
else
  python -m pytest -q
fi

echo "==> 3. Build local (sanity) — opcional se Docker disponível"
if command -v docker >/dev/null 2>&1; then
  docker compose config >/dev/null
fi

echo "==> 4. Push para GitHub"
git push origin "${MAIN_BRANCH}"

if [ -z "${DEPLOY_HOST:-}" ] || [ -z "${DEPLOY_USER:-}" ]; then
  echo "⚠ DEPLOY_HOST/DEPLOY_USER não configurados — parando antes do SSH."
  echo "  Configure no .env e rode novamente para concluir o deploy remoto."
  exit 0
fi

SSH_OPTS=()
if [ -n "${DEPLOY_SSH_KEY:-}" ]; then
  SSH_OPTS+=(-i "${DEPLOY_SSH_KEY}")
fi
REMOTE="${DEPLOY_USER}@${DEPLOY_HOST}"
REMOTE_PATH="${DEPLOY_PATH:-/opt/piam-casehub}"

echo "==> 5-9. Atualizando código e serviços em ${REMOTE}:${REMOTE_PATH}"
ssh "${SSH_OPTS[@]}" "${REMOTE}" bash -se <<EOF
set -euo pipefail
cd "${REMOTE_PATH}"
git fetch --all
git reset --hard "origin/${MAIN_BRANCH}"
docker compose up -d --build
docker compose exec -T web alembic upgrade head
docker compose restart web bot
EOF

echo "==> 10. Smoke test remoto"
ssh "${SSH_OPTS[@]}" "${REMOTE}" "curl -fsS http://localhost:8000/health" \
  && echo "✓ Deploy concluído" \
  || { echo "✗ Smoke test remoto falhou"; exit 1; }
