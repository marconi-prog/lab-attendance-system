# Modelagem do banco (MySQL 8 / InnoDB, utf8mb4)

Datas/horas em `DATETIME` **UTC**; `reference_date` é a data **local** (America/Recife) da emissão.
Schema versionado em `backend/migrations/versions/0001_schema_inicial.py`.

```text
users ──< user_counters >── counters
  │                            │
  ├──< counter_sessions >──────┤
  │                            │
  ├──< calls >── tickets ──< ticket_status_history
  ├──< attendances >─┘  (1:1)
  └──< audit_logs
daily_sequences (sequência por dia/categoria)   queue_states (ciclo de prioridade do dia)
token_blocklist (JWT revogados)
```

## Tabelas

### users
| coluna | tipo | regras |
|---|---|---|
| id | INT PK | |
| name | VARCHAR(120) | not null |
| email | VARCHAR(180) | **UNIQUE**, minúsculo |
| password_hash | VARCHAR(255) | scrypt (Werkzeug) — nunca texto puro |
| role | ENUM('ADMIN','ATTENDANT') | índice |
| active | BOOL | desativar = perde acesso imediatamente |
| created_at, updated_at | DATETIME | |

### counters
`id`, `name` VARCHAR(60), `number` INT **UNIQUE**, `active`, `created_at`, `updated_at`.

### user_counters (N:N)
PK (`user_id`, `counter_id`), FKs com `ON DELETE CASCADE`. Guichês que o atendente pode operar.

### counter_sessions
`id`, `counter_id` FK, `user_id` FK, `opened_at`, `closed_at` (NULL = aberta).
Índices (`counter_id`,`closed_at`) e (`user_id`,`closed_at`). Exclusividade garantida por
`SELECT … FOR UPDATE` no guichê ao abrir a sessão.

### tickets
| coluna | tipo | regras |
|---|---|---|
| id | INT PK | |
| code | VARCHAR(16) | **UNIQUE** — `YYMMDD-PPSQ` (ex.: `261110-SP001`) |
| type | ENUM('SP','SE','SG') | |
| status | ENUM(8 estados) | alterado só pela máquina de estados |
| daily_sequence | SMALLINT | 1–999 |
| reference_date | DATE | data local |
| issued_at, updated_at | DATETIME | |

Constraints/índices: **UNIQUE(reference_date, type, daily_sequence)**;
`ix_tickets_queue(status, reference_date, type, issued_at, id)` — cobre a seleção da próxima senha;
`ix_tickets_reference_date_type` — relatórios.

### ticket_status_history
`id`, `ticket_id` FK (CASCADE), `from_status`, `to_status`, `user_id` FK (SET NULL), `counter_id` FK (SET NULL), `created_at`.
Somente inserções — trilha completa de cada senha.

### calls
`id`, `ticket_id` FK, `user_id` FK, `counter_id` FK, `attempt_number` (1 ou 2), `called_at` (índice).
**UNIQUE(ticket_id, attempt_number)**. Cada repetição é um novo registro: o histórico nunca é sobrescrito.

### attendances
`id`, `ticket_id` FK **UNIQUE** (1:1), `user_id`, `counter_id`, `started_at`, `finished_at`,
`duration_seconds`, `result` ENUM('EM_ANDAMENTO','CONCLUIDO').

### audit_logs
`id`, `user_id` FK (SET NULL), `action`, `entity`, `entity_id`, `details` JSON (sem dados sensíveis),
`ip_address`, `created_at`. Índices: `created_at`, `action`, `user_id`, (`entity`,`entity_id`).

### daily_sequences
`id`, `reference_date`, `ticket_type`, `last_sequence`. **UNIQUE(reference_date, ticket_type)** —
a sequência reinicia naturalmente a cada dia.

### queue_states (adicional)
`id`, `reference_date` **UNIQUE**, `last_called_type`, `closed_at`, `updated_at`.
Linha bloqueada a cada chamada: serializa a seleção e guarda a posição do ciclo de prioridade.

### token_blocklist (adicional)
`id`, `jti` **UNIQUE**, `token_type`, `user_id`, `expires_at`, `revoked_at`.

## Máquina de estados

```text
EMITIDA → AGUARDANDO → CHAMADA → EM_ATENDIMENTO → ATENDIDA
                │          │            ▲
                │          ▼            │
                │   CHAMADA_NOVAMENTE ──┘
                │          │
                ▼          ▼
           DESCARTADA  NAO_COMPARECEU
```
(O valor no banco é `NAO_COMPARECEU`; a interface exibe "Não compareceu".)

## Transações

| Operação | Bloqueios |
|---|---|
| Emitir senha | `daily_sequences` (linha do dia/categoria) `FOR UPDATE` |
| Chamar próxima | `queue_states` (linha do dia) `FOR UPDATE` → `tickets` `FOR UPDATE SKIP LOCKED` |
| Repetir / iniciar / finalizar / ausência | `tickets` (a senha) `FOR UPDATE` |
| Abrir sessão de guichê | `counters` (o guichê) `FOR UPDATE` |
| Encerrar expediente | `queue_states` → `tickets` aguardando `FOR UPDATE` |

Ordem de bloqueio consistente (queue_states → tickets) evita deadlocks; os residuais são reexecutados.
