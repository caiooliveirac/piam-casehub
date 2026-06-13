# AI Handoff — PIAM CaseHub

Documento para a próxima IA/dev entender o projeto rápido e mexer com segurança.

## Objetivo do sistema

Receber casos clínicos do PIAM por Telegram (texto + ECG), **estruturar** os
dados, **padronizar** no formato textual PIAM e **acompanhar** em um dashboard.
O sistema **não** dá diagnóstico nem conduta — apenas organiza, parseia, formata
e rastreia. Toda interpretação clínica é humana.

## Stack

Python 3.12 · FastAPI · python-telegram-bot v21 · SQLAlchemy 2 · Alembic ·
PostgreSQL · Jinja2/HTMX/Tailwind(CDN) · Pytest · Ruff · Docker Compose · Nginx.

## Estrutura de pastas

```
app/
  config.py            # Settings (pydantic-settings); lê .env; aceita ADMIN_ID/GROUP_ID legados
  db.py                # engine, SessionLocal, Base, get_session
  models/              # SQLAlchemy: case, message, attachment, audit, user, ecg
  schemas/case.py      # Pydantic: ParsedCase, CaseUpdate, CaseSummary
  services/
    case_parser.py     # *** PARSER (regex determinístico) ***
    piam_formatter.py  # *** FORMATO PIAM ***
    telegram_ingest.py # cria caso, public_id, vincula mensagens/anexos
    file_storage.py    # salvar/sanitizar arquivos, classificar anexo
    metrics.py         # métricas do dashboard + export_anonymized_cases()
    audit.py           # audit.record(...)
  bot/
    handlers.py        # *** TELEGRAM: comandos e mensagens ***
    runner.py          # long polling (serviço `bot`)
  web/
    routes.py          # *** DASHBOARD: rotas FastAPI ***
    auth.py            # hash/verify senha, sessão, login guard
    templates/         # base, login, dashboard, cases_list, case_detail, metrics
  migrations/          # Alembic (versions/0001_initial.py)
tests/                 # test_parser, test_piam_formatter, test_health
scripts/               # bootstrap, deploy, create_admin, smoke_test
docs/                  # esta pasta
```

## Arquivos mais importantes

- `app/services/case_parser.py` — extração de campos do texto livre.
- `app/services/piam_formatter.py` — geração do texto PIAM canônico.
- `app/services/telegram_ingest.py` — orquestra criação de caso e `public_id`.
- `app/bot/handlers.py` — entrada do Telegram (acesso, comandos, anexos).
- `app/web/routes.py` — todas as páginas do dashboard.

## Onde mexer para…

| Tarefa | Arquivo |
|---|---|
| **Parser** (novos campos, melhorar regex) | `app/services/case_parser.py` (+ `schemas/case.py` se novo campo) |
| **Formato PIAM** (layout, regras de vazio) | `app/services/piam_formatter.py` (atualize `REQUIRED_SECTIONS` e testes) |
| **Dashboard** (páginas, filtros, métricas) | `app/web/routes.py` + `app/web/templates/*` + `app/services/metrics.py` |
| **Telegram** (comandos, fluxo de anexo) | `app/bot/handlers.py` (registre no `app/bot/runner.py`) |
| **Modelo de dados** | `app/models/*` + nova migração Alembic |
| **Auth** | `app/web/auth.py` |

## Como o parser e o formatter conversam

`parse_case(text) -> ParsedCase` (campos `None` quando não encontrados) →
`format_from_parsed(parsed) -> str`. O formatter aplica:
- identificação ausente → rótulo vazio após os dois-pontos;
- clínico importante ausente → `Não informado` (via `_clinical`, hoje usado de
  forma conservadora; a maioria usa vazio para não poluir);
- **nunca inventa** texto clínico.

`telegram_ingest` também guarda vitais (`PA/FC/FR/SatO2`) num blob em
`cases.admission_exam`, e o `format_from_case` os re-extrai para o texto PIAM.

## Próximos passos recomendados

1. **Normalização de data/hora**: derivar colunas `*_dt` a partir do texto para
   métricas confiáveis (hoje é parsing best-effort).
2. **Edição estruturada** no dashboard (hoje só status/destino/desfecho/notas/
   texto PIAM são editáveis; campos clínicos vêm do parser).
3. **Re-parse manual**: botão para reprocessar `raw_input` após melhorar o parser.
4. **Integração ECG**: ver `docs/ECG_INTEGRATION.md` e a tabela
   `ecg_interpretations` (já existe, vazia).
5. **Export de pesquisa**: implementar CSV em `metrics.export_anonymized_cases()`.
6. **Webhook do Telegram** (em vez de long polling) quando houver HTTPS estável.
7. **Testes de integração** do bot (hoje cobrimos parser/formatter/health/criação).

## Revisão / hardening aplicados (histórico)

- **Bug crítico do parser corrigido**: o rótulo `MP` em alternação no topo do
  regex casava a substring "mp" (ex.: "tempo") e estourava `AttributeError`,
  quebrando a criação de caso. Hoje `_search` é None-safe e `_labelled` agrupa a
  alternação; `MP` usa `\bMP\b`. Há teste de regressão.
- Flags clínicas (`alergias`, `contraindicação à trombólise`, `COVID`) agora
  reconhecem as formas reais do PIAM ("Nega alergias", "...trombólise? X").
- `/fechar` restrito ao admin; bot ignora mensagens de outros bots.
- Fallback de login do `.env` bloqueado para senha placeholder; `/docs`
  desabilitado em produção.

## Bugs conhecidos / limitações

- Parser é heurístico: texto fora do padrão extrai poucos campos (degrada para
  vazio/`Não informado`, nunca inventa).
- Datas/horas são strings; medianas ignoram valores não-parseáveis.
- Sem paginação na lista de casos (limite de 200).
- Filtro "com ECG" é aplicado em Python após a query (ok no volume atual).
- Follow-up curto no Telegram é só registrado como mensagem (não re-parseia o
  caso); o `raw_input` original é preservado para re-parse futuro.
- Chamadas de banco são síncronas dentro de handlers async do bot — ok no
  volume atual; migrar para fila/worker se crescer.
- Auth é de sessão única por senha; sem 2FA/rotação.
- Anexos são baixados pelo bot; se o download falhar, o `Attachment` é criado
  sem `storage_path` (metadados preservados, arquivo ausente) — ver logs.
- Anotações usam `Optional[...]`/`timezone.utc` de propósito (portabilidade
  3.9–3.12); Ruff está configurado para não "modernizar" isso.
