# Deploy — PIAM CaseHub (AWS + Docker + Nginx + HTTPS)

Passo a passo realista para subir em `piam.mnrs.com.br`. Não há credenciais
versionadas — tudo vem do `.env` da instância ou dos *secrets* do GitHub.

A instância AWS é **compartilhada** com outros projetos (giro-de-leitos,
checagemdebases, etc.). Por isso o PIAM publica a web em **`127.0.0.1:8060`**
(as portas 8000/8001/8050/8080 já estão em uso). O Postgres do PIAM roda no
**próprio container** (`db`), isolado na rede do compose — não conflita com
outros bancos do host.

## Deploy via GitHub Actions (recomendado)

`.github/workflows/deploy.yml` (modelado nos projetos que já acessam a mesma
EC2) roda a cada push na `main`: testa (ruff+pytest), conecta por SSH no EC2,
faz rsync do código, renderiza o `.env` de produção a partir dos *secrets*,
sobe com `docker compose up -d --build`, aplica migrações, reinicia `web`/`bot`,
roda smoke test em `/health` e notifica no Telegram.

`.github/workflows/ci.yml` roda em todo push/PR (ruff, pytest, docker build).

**Secrets já configurados** no repo `caiooliveirac/piam-casehub`:

| Secret | Função |
|---|---|
| `PROD_SSH_HOST` | host da EC2 (`samu` = `56.125.255.58`) |
| `PROD_SSH_USER` | `ubuntu` |
| `PROD_SSH_KEY` | chave privada de deploy (`~/.ssh/caio_ec2_2026`) |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_ID`, `TELEGRAM_GROUP_ID` | bot |
| `POSTGRES_PASSWORD`, `SECRET_KEY`, `ADMIN_PASSWORD` | app |

Deploy manual pelo UI: aba **Actions → Deploy → Run workflow** (workflow_dispatch).

Diretório de deploy no servidor: `/home/ubuntu/piam-casehub`.

> O script `scripts/deploy.sh` continua disponível como alternativa manual a
> partir da sua máquina (usa `DEPLOY_HOST/USER/KEY/PATH` do `.env`).

---

## Setup inicial (uma vez, por baixo)

## 0. Pré-requisitos na instância AWS

- Docker + plugin Compose instalados.
- Nginx instalado (`sudo apt install nginx`).
- (Opcional) Certbot (`sudo apt install certbot python3-certbot-nginx`).
- Porta 80/443 abertas no Security Group.
- DNS: registro **A** de `piam.mnrs.com.br` apontando para o IP elástico da
  instância. **HTTPS só funciona depois que o DNS propagar.**

## 1. Variáveis de deploy

No `.env` local (para `scripts/deploy.sh`) e/ou no `.env` do servidor:

```env
DEPLOY_HOST=          # ex.: 12.34.56.78 ou ec2-...compute.amazonaws.com
DEPLOY_USER=          # ex.: ubuntu
DEPLOY_PATH=/opt/piam-casehub
DEPLOY_SSH_KEY=       # ex.: ~/.ssh/minha-chave.pem (opcional)
```

> Estas variáveis **não foram preenchidas** no scaffold — preencha com os dados
> reais da sua instância. Sem `DEPLOY_HOST/DEPLOY_USER`, o `deploy.sh` roda os
> testes e o push e para antes do SSH, com mensagem clara.

## 2. Primeiro deploy (manual, uma vez)

```bash
# na instância
sudo mkdir -p /opt/piam-casehub && sudo chown "$USER" /opt/piam-casehub
cd /opt/piam-casehub
git clone git@github.com:caiooliveirac/piam-casehub.git .
cp .env.example .env        # preencha TODOS os segredos (token, senhas, SECRET_KEY)
docker compose up -d --build
docker compose exec web alembic upgrade head
docker compose exec web python scripts/create_admin.py
curl -f http://localhost:8060/health
```

## 3. Deploys seguintes (automatizado)

Do seu computador, na branch principal:

```bash
./scripts/deploy.sh
```

Ele: confirma a branch → roda `pytest` → valida `docker compose config` → faz
`git push` → conecta por SSH → `git reset --hard origin/main` →
`docker compose up -d --build` → `alembic upgrade head` → reinicia `web`/`bot` →
smoke test em `/health`. É **idempotente**.

## 4. Nginx (reverse proxy)

```bash
sudo cp nginx/piam.mnrs.com.br.conf /etc/nginx/sites-available/piam.mnrs.com.br.conf
sudo ln -s /etc/nginx/sites-available/piam.mnrs.com.br.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

O server block faz proxy para `127.0.0.1:8060` (porta publicada só no localhost
pelo `docker-compose.yml`) e limita uploads a `25M`.

## 5. HTTPS (Certbot)

**Somente após o DNS apontar para a instância:**

```bash
sudo certbot --nginx -d piam.mnrs.com.br
```

O Certbot edita o server block, adiciona o bloco 443 e configura renovação
automática. Se o DNS ainda não propagou, **não rode** — ele falhará na validação.

Depois, ajuste `BASE_URL=https://piam.mnrs.com.br` e `APP_ENV=production` no
`.env` do servidor (ativa cookie de sessão `https_only`) e reinicie:

```bash
docker compose restart web bot
```

## 6. Operação

```bash
docker compose ps                 # status
docker compose logs -f web        # logs da web
docker compose logs -f bot        # logs do bot
docker compose exec web alembic upgrade head   # migração após deploy
docker compose exec db pg_dump -U piam piam > backup_$(date +%F).sql  # backup
```

Volumes persistentes: `pgdata` (banco) e `uploads` (arquivos em
`/data/uploads`). **Inclua ambos na rotina de backup.**

## Troubleshooting

- **Bot não responde:** confira `TELEGRAM_BOT_TOKEN`, `TELEGRAM_GROUP_ID` e se o
  privacy mode está desligado. Veja `docker compose logs -f bot`.
- **502 no Nginx:** o serviço `web` provavelmente não subiu — `docker compose ps`.
- **Certbot falha:** DNS ainda não propagou ou porta 80 bloqueada.
- **Migração falha:** rode `alembic upgrade head` manualmente e leia o erro.
