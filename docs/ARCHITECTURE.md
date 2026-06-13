# Arquitetura — PIAM CaseHub

## Visão geral

PIAM CaseHub é um MVP de três processos que compartilham uma imagem Docker e um
banco PostgreSQL:

- **web** — FastAPI/Uvicorn: dashboard administrativo e API `/health`.
- **bot** — python-telegram-bot (long polling): ingestão dos casos.
- **db** — PostgreSQL.

O código de domínio (parser, formatter, ingestão, métricas) é **independente do
transporte**: o bot e a web chamam os mesmos serviços. Isso mantém a lógica
testável e reaproveitável.

## Diagrama textual

```
                 ┌─────────────────────────────────────────────┐
   Telegram      │                  PIAM CaseHub               │
  (grupo PIAM)   │                                             │
       │         │   ┌─────────┐      ┌────────────────────┐   │
  texto/ECG ────────▶│  bot    │────▶ │ services/          │   │
       │         │   │ handlers│      │  case_parser       │   │
       │         │   └─────────┘      │  piam_formatter    │   │
       │         │                    │  telegram_ingest   │   │
       │         │   ┌─────────┐      │  file_storage      │   │
  admin login ──────▶│  web    │────▶ │  metrics / audit   │   │
  (navegador)    │   │ routes  │      └─────────┬──────────┘   │
       │         │   └─────────┘                │              │
       │         │                              ▼              │
       │         │                       ┌────────────┐        │
       │         │                       │ PostgreSQL │        │
       │         │                       └────────────┘        │
       │         │                  /data/uploads (volume)     │
                 └─────────────────────────────────────────────┘
                              ▲
                         Nginx + HTTPS
                       piam.mnrs.com.br
```

## Fluxo Telegram → caso → dashboard

1. Mensagem chega no grupo configurado (`TELEGRAM_GROUP_ID`).
2. `bot/handlers` verifica autorização (grupo/admin) e classifica:
   - **texto clínico** → `telegram_ingest.create_case_from_text()`:
     - `case_parser.parse_case()` extrai campos;
     - `piam_formatter.format_from_parsed()` gera o texto PIAM;
     - persiste `Case` com `public_id` sequencial (`PIAM-AAAA-NNNNNN`);
     - registra `AuditLog` e a `TelegramMessage`.
   - **arquivo (foto/PDF)** → baixa, sanitiza o nome, salva em
     `/data/uploads/<public_id>/`, cria `Attachment` com metadados, vincula ao
     caso aberto mais recente do chat.
3. O bot responde no grupo com `public_id`, status, prévia PIAM e link do dashboard.
4. No dashboard, o admin acompanha, edita status/destino/desfecho e ajusta o
   texto PIAM final. Toda edição relevante vira `AuditLog`.

## Modelo de dados

| Tabela | Papel |
|---|---|
| `cases` | Registro clínico central (identificação, timeline, narrativa, vitais, desfecho, `raw_input`, `piam_formatted_text`). |
| `telegram_messages` | Toda mensagem recebida, rastreável ao caso (`case_id` nullable). |
| `attachments` | Arquivos recebidos, com `storage_path`, `mime_type`, `attachment_type`. |
| `audit_logs` | Ações auditáveis (`actor_type`, `action`, `case_id`, `payload_json`). |
| `admin_users` | Usuário admin web, senha em hash. |
| `ecg_interpretations` | Placeholder para leitura de ECG (máquina/IA/cardiologista). |

`status` do caso: `novo`, `em_avaliacao`, `orientado`, `transferido`,
`encerrado`, `cancelado`. Os três primeiros são considerados "abertos" para fins
de vincular follow-ups e anexos.

## Decisões técnicas e trade-offs

- **Campos de data/hora como texto (`String`)** no MVP. A entrada é livre e
  ambígua (ex.: só `22:34`); guardar o texto cru evita perda de informação. As
  métricas de tempo fazem _parsing_ best-effort e ignoram o que não conseguem
  interpretar. _Trade-off:_ sem garantia de tipo; evolução futura pode adicionar
  colunas `*_dt` derivadas.
- **Parser determinístico (regex), sem IA.** Previsível, testável, sem
  dependência externa nem custo. _Trade-off:_ cobertura limitada; texto fora do
  padrão extrai menos campos (degrada para vazio/"Não informado", nunca inventa).
- **Bot e web como serviços separados, mesma imagem.** Falha de um não derruba o
  outro; deploy e logs independentes. _Trade-off:_ dois containers.
- **Tailwind via CDN + HTMX, sem build de frontend.** Zero toolchain de JS.
  _Trade-off:_ depende de CDN; troca por build se necessário.
- **Auth simples (sessão assinada + hash PBKDF2 stdlib).** Sem dependência
  nativa (bcrypt) e suficiente para um painel interno restrito. _Trade-off:_ não
  é um IdP; adequado a poucos administradores.
- **`status` como string documentada, não Enum do banco.** Migrações mais
  simples. _Trade-off:_ validação fica na aplicação.
- **Anotações com `Optional[...]`/`timezone.utc`.** Roda em 3.9–3.12, embora o
  alvo seja 3.12 (Docker). Conservador e portável.
