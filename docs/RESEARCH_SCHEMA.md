# Research Schema & LGPD — PIAM CaseHub

Como transformar os casos em uma base de pesquisa, com cuidado de dados pessoais
sensíveis (LGPD, Lei 13.709/2018).

## Princípios

- Dados de saúde são **dados pessoais sensíveis** (art. 5º, II; art. 11).
- Pesquisa científica tem base legal possível (art. 7º, IV; art. 11, II, "c"),
  mas exige **minimização**, **anonimização sempre que possível** e, para
  pesquisa formal, **aprovação em CEP/CONEP** e termo de consentimento quando
  aplicável.
- **Nunca** enviar dados clínicos a serviços externos (incl. IA de terceiros)
  sem base legal e autorização explícita. Veja [SECURITY.md](SECURITY.md).

## Classificação dos campos

### Identificáveis (NÃO exportar em dataset de pesquisa)

| Campo | Por quê |
|---|---|
| `patient_name` | Identificação direta |
| `patient_birth_date` | Quase-identificador forte |
| `companion` | Pode identificar terceiros |
| `health_plan` | Quase-identificador |
| `mp` | Identifica o profissional |
| `hma`, `current_status`, `research_notes` | Texto livre pode conter nomes/detalhes |
| `raw_input`, `piam_formatted_text` | Contêm a narrativa completa |
| `telegram_*` (mensagens) | Identificam autor/remetente |
| `storage_path`, anexos | Imagens/PDF podem conter nome do paciente |

### Exportáveis de forma anonimizada (com cautela)

| Campo | Observação |
|---|---|
| `public_id` | Pseudônimo do caso (não reversível externamente) |
| `status`, `destination`, `outcome` | Desfecho |
| `patient_age` | Preferir **faixas etárias** (ex.: 60–69) |
| `origin_unit` | Avaliar agregação se a unidade for pequena (risco de reidentificação) |
| `killip`, vitais agregados | Clínico, não identificável isoladamente |
| `admission_at`, `ecg_at`, `activation_at` | Preferir **deltas de tempo** (min) a timestamps absolutos |

> A função `services/metrics.export_anonymized_cases()` já materializa um
> subconjunto seguro (`ANONYMIZED_FIELDS`) e exclui identificadores diretos. É um
> **placeholder**: hoje retorna dicts; a serialização CSV/Parquet e a
> transformação para faixas/deltas são trabalho futuro.

## Dataset analítico sugerido

Uma linha por caso, colunas derivadas e desidentificadas:

```
case_pseudo_id            # = public_id
age_band                  # faixa etária (10 em 10)
origin_unit_grouped       # unidade ou "Outros" se rara
killip
admission_to_ecg_min      # delta numérico
ecg_to_activation_min     # delta numérico
status_final
destination
outcome
has_ecg_attachment        # bool
data_completeness_pct      # % de campos núcleo preenchidos
```

Sem nomes, datas de nascimento, narrativa livre ou conteúdo de anexos.

## Trilha de auditoria

Toda criação/edição/encerramento e adição de anexo gera `audit_logs`
(`actor_type`, `action`, `case_id`, `payload_json`, `created_at`). Isso suporta
rastreabilidade exigida em pesquisa e governança de dados. O `payload_json`
**não** deve conter dados sensíveis além do necessário (hoje guarda só nomes de
campos/tipos).

## Checklist para pesquisa formal

- [ ] Protocolo aprovado por **CEP/CONEP**.
- [ ] Base legal definida (consentimento e/ou interesse legítimo/pesquisa).
- [ ] Plano de **anonimização/pseudonimização** documentado.
- [ ] Minimização: exportar só o necessário.
- [ ] Controle de acesso ao dataset e registro de quem exporta.
- [ ] Acordo explícito antes de usar qualquer serviço externo de IA.
- [ ] Política de retenção e descarte.
