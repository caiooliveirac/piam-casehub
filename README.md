# PIAM CaseHub

Ferramenta para **ingestão, padronização e acompanhamento de casos clínicos do
PIAM** (Protocolo de Infarto Agudo do Miocárdio). Casos chegam por um **bot de
Telegram** (texto + imagens/PDF de ECG), são **parseados** para campos
estruturados, **formatados no padrão textual PIAM** e acompanhados em um
**dashboard web administrativo**.

> ⚠️ Este sistema **organiza e padroniza** casos. Ele **não** faz interpretação
> diagnóstica automática nem recomendação terapêutica. Decisão clínica é sempre
> humana.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Backend / Web | Python 3.12 · FastAPI · Uvicorn |
| Bot | python-telegram-bot v21 |
| Banco | PostgreSQL 16 |
| ORM / Migrações | SQLAlchemy 2.x · Alembic |
| Templates | Jinja2 · HTMX · Tailwind (CDN) |
| Auth admin | Login com senha (hash PBKDF2) |
| Execução | Docker Compose (`web`, `bot`, `db`) |
| Proxy / TLS | Nginx · Certbot |
| Testes / Lint | Pytest · Ruff |

---

## Rodar local (Docker)

```bash
cp .env.example .env       # preencha os segredos (token do bot, senha admin, etc.)
docker compose up -d --build
docker compose exec web alembic upgrade head
docker compose exec web python scripts/create_admin.py
```

Ou em um passo só: `./scripts/bootstrap.sh`.

- **Web/Dashboard:** http://localhost:8000 → login em `/login`
- **Health:** http://localhost:8000/health

## Rodar local (sem Docker, dev)

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
export DATABASE_URL="sqlite+pysqlite:///:memory:"   # ou um Postgres local
uvicorn app.main:app --reload
```

---

## Comandos úteis

```bash
# Testes
pytest -q

# Lint / format
ruff check .
ruff check --fix .

# Migrações
docker compose exec web alembic upgrade head
docker compose exec web alembic revision --autogenerate -m "mudança"

# Validar compose
docker compose config

# Smoke test
./scripts/smoke_test.sh http://localhost:8000

# Deploy
./scripts/deploy.sh
```

---

## Bot do Telegram

O bot roda como serviço próprio (`bot`) usando a mesma imagem. Comandos:

| Comando | Ação |
|---|---|
| (texto livre) | Cria/atualiza um caso a partir da história clínica |
| foto / PDF | Anexa ECG ao caso aberto mais recente do chat |
| `/novo <texto>` | Cria um caso novo |
| `/casos` | Lista os últimos casos |
| `/fechar <public_id>` | Encerra um caso |
| `/resumo <public_id>` | Devolve o texto no padrão PIAM |

Restrições de acesso: mensagens só são processadas no `TELEGRAM_GROUP_ID`
configurado; comandos privados só do `TELEGRAM_ADMIN_ID`. Veja
[docs/SECURITY.md](docs/SECURITY.md).

---

## Dashboard

- `/dashboard` — cards de volume, status, tempos medianos, ECG anexado, sem desfecho.
- `/cases` — lista com filtros (nome, status, unidade, data, com ECG, sem desfecho).
- `/cases/{public_id}` — detalhe: dados estruturados, texto PIAM, mensagens,
  anexos, trilha de auditoria, e campos editáveis (status/destino/desfecho/
  notas/texto PIAM final).
- `/metrics` — métricas para pesquisa.

---

## Deploy

Resumo (detalhes em [docs/DEPLOY.md](docs/DEPLOY.md)):

1. Configure `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PATH`, `DEPLOY_SSH_KEY` no `.env`.
2. `./scripts/deploy.sh` — roda testes, dá push, atualiza o servidor por SSH,
   aplica migrações e roda smoke test.
3. Nginx + Certbot para `piam.mnrs.com.br`.

---

## Documentação

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — visão geral e decisões técnicas
- [docs/AI_HANDOFF.md](docs/AI_HANDOFF.md) — guia rápido para a próxima IA/dev
- [docs/DEPLOY.md](docs/DEPLOY.md) — deploy AWS/Nginx/HTTPS
- [docs/RESEARCH_SCHEMA.md](docs/RESEARCH_SCHEMA.md) — base de pesquisa e LGPD
- [docs/SECURITY.md](docs/SECURITY.md) — ameaças e mitigação
- [docs/ECG_INTEGRATION.md](docs/ECG_INTEGRATION.md) — ponto de integração para ECG

---

## Estrutura

```
app/        config, db, models, schemas, services, bot, web, migrations
tests/      parser, formatter, health/criação de caso
docs/       documentação
nginx/      server block do subdomínio
scripts/    bootstrap, deploy, create_admin, smoke_test
```

Segredos ficam só no `.env` (fora do git). Veja `.env.example`.
