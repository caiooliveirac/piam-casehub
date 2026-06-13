# Integração futura — Interpretação de ECG

Este scaffold **não** interpreta ECG. Ele recebe, armazena e relaciona os
arquivos ao caso, deixando o ponto de acoplamento pronto para uma tecnologia
futura (leitura por máquina, IA e/ou laudo do cardiologista).

## Onde os arquivos chegam

1. Usuário envia **foto** ou **PDF** de ECG no grupo do Telegram.
2. `app/bot/handlers.py::on_file` baixa o arquivo, classifica o tipo
   (`ecg_image`, `ecg_pdf`, `clinical_document`, `other` — ver
   `file_storage.classify_attachment`) e salva em
   `/data/uploads/<public_id>/<nome-sanitizado>`.
3. Cria um `Attachment` com metadados (`telegram_file_id`, `file_name`,
   `mime_type`, `storage_path`, `attachment_type`) **vinculado ao caso aberto
   mais recente** do chat (ou cria um caso-stub para não perder o arquivo).

## Como anexos se relacionam ao caso

```
cases (1) ──── (N) attachments ──── (N) ecg_interpretations
```

`attachments.case_id` liga o arquivo ao caso. A tabela
`ecg_interpretations` (já existe, **vazia** no MVP) é o destino das leituras.

## Onde acoplar a interpretação

Crie um serviço, ex. `app/services/ecg_interpreter.py`, acionado **após**
`on_file` persistir o `Attachment` (de forma assíncrona / fila, para não
bloquear o bot). Ele deve:

1. Ler `attachment.storage_path`.
2. Chamar o motor de interpretação (máquina/IA) **respeitando a LGPD** — não
   enviar a serviço externo sem base legal e autorização (ver
   [SECURITY.md](SECURITY.md) e [RESEARCH_SCHEMA.md](RESEARCH_SCHEMA.md)).
3. Gravar uma linha em `ecg_interpretations` com o resultado.
4. **Nunca** sobrescrever o laudo do cardiologista; `cardiologist_final_read` é
   sempre a fonte de verdade humana.

> Princípio mantido: o sistema **sugere/organiza**, não decide. Qualquer leitura
> automática é um insumo, não conduta.

## Contrato sugerido

```json
{
  "case_public_id": "PIAM-2026-000001",
  "attachment_id": 123,
  "ecg_acquired_at": "2026-06-02T22:34:00-03:00",
  "machine_read": "",
  "ai_read": "",
  "cardiologist_final_read": "",
  "stemi_suspected": null,
  "territory": "",
  "confidence": null,
  "warnings": []
}
```

Mapeamento para `ecg_interpretations`:

| Campo do contrato | Coluna | Tipo |
|---|---|---|
| `case_public_id` | (resolver para `case_id`) | FK |
| `attachment_id` | `attachment_id` | FK |
| `ecg_acquired_at` | `ecg_acquired_at` | String (ISO) |
| `machine_read` | `machine_read` | Text |
| `ai_read` | `ai_read` | Text |
| `cardiologist_final_read` | `cardiologist_final_read` | Text |
| `stemi_suspected` | `stemi_suspected` | Boolean nullable |
| `territory` | `territory` | String |
| `confidence` | `confidence` | Float nullable |
| `warnings` | `warnings` | Text (JSON list) |

## Próximos passos de produto

- UI no `case_detail` para exibir/editar `ecg_interpretations` e o laudo final.
- Fila/worker para processamento assíncrono.
- Métricas de tempo até laudo e concordância máquina × cardiologista.
- Política de retenção de imagens e consentimento.
