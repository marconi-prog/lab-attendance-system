# Diagramas UML

Veja também os [casos de uso](casos-de-uso.md), com atores, pré-condições, fluxo e alternativas.

## Estados da senha

Fonte: [`TicketStateMachine`](../../../backend/app/services/state_machine.py).
O cliente presente pode iniciar atendimento após a primeira chamada; a segunda não é obrigatória.

```mermaid
stateDiagram-v2
    [*] --> EMITIDA
    EMITIDA --> AGUARDANDO
    AGUARDANDO --> CHAMADA
    AGUARDANDO --> DESCARTADA: encerramento
    CHAMADA --> EM_ATENDIMENTO: cliente presente
    CHAMADA --> CHAMADA_NOVAMENTE: ultima chamada
    CHAMADA_NOVAMENTE --> EM_ATENDIMENTO: cliente presente
    CHAMADA_NOVAMENTE --> NAO_COMPARECEU: ausencia confirmada
    EM_ATENDIMENTO --> ATENDIDA
    ATENDIDA --> [*]
    NAO_COMPARECEU --> [*]
    DESCARTADA --> [*]
```

## Sequência de chamada concorrente

```mermaid
sequenceDiagram
    actor AA as Atendente ou gestor autorizado
    participant API as API Flask
    participant Q as QueueService
    participant DB as MySQL InnoDB
    participant P as Painel publico
    AA->>API: POST chamar proxima (JWT e sessao)
    API->>Q: call_next(user_id, session)
    Q->>DB: bloquear guiche e revalidar sessao/permissao
    Q->>DB: bloquear queue_states do dia
    Q->>DB: verificar guiche livre e contar filas
    Q->>DB: reservar ticket com FOR UPDATE SKIP LOCKED
    Q->>DB: transicao + chamada + auditoria + ciclo
    Q->>DB: COMMIT
    Q-->>API: senha e chamada
    Q-->>P: Socket.IO com anuncio
    API-->>AA: resposta JSON
    Note over Q,DB: Outra chamada aguarda o bloqueio e reavalia a fila
```

## Responsabilidades

```mermaid
classDiagram
    class TicketService {
        issue()
    }
    class QueueService {
        select_next_type()
        call_next()
        recall()
    }
    class AttendanceService {
        open_session()
        start()
        finish()
        no_show()
    }
    class TicketStateMachine {
        transition()
    }
    class PanelService {
        snapshot()
        publish()
    }
    class ReportService {
        daily()
        monthly()
    }
    TicketService ..> TicketStateMachine
    QueueService ..> TicketStateMachine
    AttendanceService ..> TicketStateMachine
    QueueService ..> PanelService
```

As operações públicas são anônimas para cliente/painel; as demais exigem autenticação.
O gestor acumula atendimento em guichês autorizados e administração; atendentes comuns não
possuem cadastros ou relatórios administrativos. Consulte a matriz de permissões em
[`requirements`](../../requirements/README.md).
