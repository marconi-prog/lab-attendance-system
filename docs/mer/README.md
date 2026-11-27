# Modelo Entidade-Relacionamento

Modelo lógico derivado dos [modelos SQLAlchemy](../../backend/app/models) e das
[migrations](../../backend/migrations/versions). Tipos, índices e política de UTC em
[`database.md`](../database.md). Renderização Mermaid disponível no GitHub.

```mermaid
erDiagram
    USERS ||--o{ USER_COUNTERS : autorizado
    COUNTERS ||--o{ USER_COUNTERS : permite
    USERS ||--o{ COUNTER_SESSIONS : abre
    COUNTERS ||--o{ COUNTER_SESSIONS : recebe
    TICKETS ||--o{ CALLS : chamadas
    USERS ||--o{ CALLS : chama
    COUNTERS ||--o{ CALLS : anuncia
    TICKETS ||--o| ATTENDANCES : atendimento
    USERS ||--o{ ATTENDANCES : atende
    COUNTERS ||--o{ ATTENDANCES : local
    TICKETS ||--o{ TICKET_STATUS_HISTORY : transicoes
    USERS o|--o{ TICKET_STATUS_HISTORY : responsavel
    COUNTERS o|--o{ TICKET_STATUS_HISTORY : contexto
    USERS o|--o{ AUDIT_LOGS : ator
    USERS o|--o{ TOKEN_BLOCKLIST : revoga
    USERS {
        int id PK
        string email UK
        string password_hash
        enum role
        boolean active
        int active_manager_slot UK
    }
    COUNTERS {
        int id PK
        int number UK
        boolean active
    }
    USER_COUNTERS {
        int user_id PK,FK
        int counter_id PK,FK
    }
    TICKETS {
        int id PK
        string code UK
        enum type
        enum status
        date reference_date
        int daily_sequence
        datetime issued_at
    }
    CALLS {
        int id PK
        int ticket_id FK
        int user_id FK
        int counter_id FK
        int attempt_number
        datetime called_at
    }
    ATTENDANCES {
        int id PK
        int ticket_id FK,UK
        int user_id FK
        int counter_id FK
        datetime started_at
        datetime finished_at
    }
    DAILY_SEQUENCES {
        int id PK
        date reference_date
        enum ticket_type
        int last_sequence
    }
    QUEUE_STATES {
        int id PK
        date reference_date UK
        enum last_called_type
        datetime closed_at
    }
```

`daily_sequences` e `queue_states` são controles por dia/categoria, sem chave estrangeira para
uma senha individual. `calls` tem unicidade por senha/tentativa; `tickets`, por dia/tipo/sequência.
As relações opcionais de auditoria preservam histórico quando a referência ao usuário é removida.
