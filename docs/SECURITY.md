# Segurança — PIAM CaseHub

MVP com dados de saúde: o objetivo é uma base segura e auditável. Esta página
lista ameaças e mitigação inicial.

## Segredos

- **`.env` nunca é versionado** (`.gitignore` cobre `.env` e variações; só
  `.env.example` entra no git).
- Segredos vivem só no `.env` da máquina/instância: token do bot, senha admin,
  `SECRET_KEY`, credenciais do banco.
- **Logs não imprimem segredos.** O bot loga eventos, não tokens.
- `SECRET_KEY` assina os cookies de sessão — gere um valor forte e único por
  ambiente. Troca de `SECRET_KEY` invalida sessões.

## Autenticação e sessão

- Login admin com senha; armazenada como **hash PBKDF2-HMAC-SHA256** (200k
  iterações, salt aleatório) — ver `app/web/auth.py`.
- Fallback de primeiro acesso via `ADMIN_USERNAME`/`ADMIN_PASSWORD` do `.env`,
  comparado em tempo constante. Rode `scripts/create_admin.py` para criar o
  usuário no banco e **troque a senha padrão**.
- Sessão por cookie assinado (Starlette `SessionMiddleware`), `SameSite=Lax`.
  Em produção (`APP_ENV=production`) o cookie é `https_only`.

## Telegram

- O bot **só processa mensagens do grupo** `TELEGRAM_GROUP_ID`.
- Comandos privados **só do** `TELEGRAM_ADMIN_ID`; qualquer outro chat privado é
  ignorado.
- Mantenha o **privacy mode** do bot desligado apenas o necessário para receber
  as mensagens do grupo.
- O token concede controle total do bot — trate como segredo crítico. Se vazar,
  revogue no BotFather.

## Uploads

- Arquivos salvos em volume persistente `/data/uploads/<public_id>/`.
- **Nomes sanitizados** (`file_storage.sanitize_filename`): remove diretórios,
  normaliza unicode, permite só `[A-Za-z0-9._-]` — evita path traversal.
- **Limite de tamanho:** `client_max_body_size 25M` no Nginx; `MAX_UPLOAD_MB`
  documenta o limite na aplicação. Telegram também limita o tamanho do arquivo.
- Conteúdo de ECG (imagem/PDF) pode conter PII — proteja o volume e os backups.

## Banco e auditoria

- Toda ação relevante → `audit_logs` (criação, edição, encerramento, anexo).
- `payload_json` guarda só metadados (nomes de campos), não dados sensíveis.
- Backups de `pgdata` e `uploads` devem ser criptografados em repouso.

## Rede

- A porta da app é publicada só em `127.0.0.1:8060`; o acesso externo passa pelo
  Nginx (80/443).
- HTTPS via Certbot (ver [DEPLOY.md](DEPLOY.md)). Forçar HTTPS em produção.

## Modelo de ameaças (resumo)

| Ameaça | Mitigação atual | Futuro |
|---|---|---|
| Vazamento de `.env`/token | fora do git, logs limpos | secret manager, rotação |
| Acesso não autorizado ao painel | login + hash + sessão assinada | 2FA, rate limit, lockout |
| Spoofing no Telegram | filtro por grupo/admin | verificação de assinatura/webhook |
| Path traversal em upload | sanitização de nome | scan de malware, content-type allowlist |
| Reidentificação em pesquisa | export anonimizado (placeholder) | faixas/deltas, k-anonimato |
| Envio indevido a IA externa | proibido sem base legal (doc) | DLP, gating técnico |
| Perda de dados | volumes persistentes | backup automatizado + teste de restore |
| Injeção (SQL) | SQLAlchemy parametrizado | revisão contínua |

## Boas práticas operacionais

- Trocar **todas** as senhas/`SECRET_KEY` padrão antes de produção.
- Restringir acesso SSH por chave e Security Group.
- Revisar `audit_logs` periodicamente.
- Não colar dados de paciente em ferramentas externas sem autorização.
