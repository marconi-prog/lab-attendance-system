# Requisitos, rastreabilidade e plano de execução

## Agentes

| Agente | Perfil | Acesso |
|---|---|---|
| AS — Agente Sistema | ADMIN | Usuários, guichês, relatórios, auditoria, informações do sistema |
| AA — Agente Atendente | ATTENDANT | Guichê autorizado, chamar/repetir/iniciar/finalizar/ausência |
| AC — Agente Cliente | sem login | Emissão de senha no totem |

## Rastreabilidade (requisito → implementação → teste)

| Requisito | Implementação | Testes |
|---|---|---|
| Código `YYMMDD-PPSQ`, sequência por categoria, reinício diário | `TicketService.issue`, `daily_sequences` | `test_ticket_issuance.py` (padrão, independência, virada de dia, limite 999) |
| Sem duplicidade com emissões simultâneas | `SELECT … FOR UPDATE` + `UNIQUE(code)` | `test_concurrent_issuance_never_duplicates_codes` (40 threads) |
| Ciclo SP → SE/SG → SP; categorias vazias não bloqueiam | `QueueService.select_next_type` | `tests/unit/test_queue_policy.py`, `test_priority_cycle`, `test_cycle_handles_empty_categories` |
| Reserva atômica da próxima senha | `QueueService.call_next` (bloqueio de `queue_states` + `SKIP LOCKED`) | `test_concurrent_attendants_never_get_same_ticket` (10 guichês), `test_concurrent_double_click_reserves_only_one` |
| Máquina de estados | `TicketStateMachine` + `ticket_status_history` | `test_state_machine.py` (64 combinações) |
| Iniciar/finalizar, duração | `AttendanceService.start/finish` | `test_start_and_finish` |
| Ausência após duas chamadas | `recall` + `no_show` | `test_no_show_after_two_calls_releases_queue`, `test_third_call_is_not_allowed` |
| Histórico de chamadas imutável | tabela `calls` (`UNIQUE(ticket_id, attempt_number)`) | `test_recall_creates_new_call_record` |
| Painel: 5 últimas, só chamadas, tempo real, áudio | `PanelService`, namespace `/panel`, `useAnnouncer` | `test_panel_realtime.py` + E2E navegador |
| Expediente 07–17h, encerramento, America/Recife | `BusinessHours`, `DayClosingService`, `scheduler.py` | `test_business_hours`, `test_calls_blocked_outside_business_hours`, `test_day_closing_*`, `test_scheduled_closing*` |
| JWT access/refresh, revogação, hash | `AuthService`, `middlewares/auth.py` | `test_auth.py` |
| Autorização por perfil | `roles_required` via `api_route` | `test_anonymous_is_rejected`, `test_attendant_cannot_access_admin`, `test_admin_cannot_operate_counter` |
| Relatórios diário/mensal/período, filtros | `ReportService` (agregações SQL) | `test_reports.py` |
| Auditoria | `AuditService` (mesma transação) | `test_audit_log`, `test_login_is_audited_without_password` |

### Interpretações adotadas

* **"Registrar ausência"**: só é aceito após a repetição (2ª chamada). Na 1ª ausência o atendente usa
  "Repetir chamada", que anuncia "Última chamada…"; persistindo a ausência, registra-se `NAO_COMPARECEU`.
* **Após 17h**: novas chamadas são bloqueadas; repetir, iniciar, finalizar e registrar ausência de senhas
  **já chamadas** continuam permitidos ("atendimentos em andamento poderão ser finalizados").
* **Descarte**: apenas senhas `AGUARDANDO` (única transição permitida para `DESCARTADA`).
* **SE × SG**: após SP, SE tem preferência; sem SP, a ordem é SE e depois SG (leitura literal da regra).
* **Painel (alteração solicitada pelo cliente)**: além das chamadas, o painel mostra a coluna **PRÓXIMOS**
  com as senhas aguardando por fila e a ordem prevista de chamada (mesma regra do `QueueService`).
  A coluna **CHAMANDO** e as **ÚLTIMAS CHAMADAS** continuam mostrando apenas senhas efetivamente chamadas.

## Divisão em módulos (equipe de 6)

| Dev | Módulo | Principais arquivos |
|---|---|---|
| 1 | Infra, banco, migrations, CI de testes | `docker-compose.yml`, `models/`, `migrations/`, `database/` |
| 2 | Autenticação, autorização, usuários, auditoria | `auth_service`, `user_service`, `middlewares/`, `audit_service` |
| 3 | Emissão, fila, máquina de estados, expediente | `ticket_service`, `queue_service`, `state_machine`, `day_closing_service` |
| 4 | Atendimento, tempo real, relatórios | `attendance_service`, `sockets/`, `realtime`, `report_service` |
| 5 | Frontend: base, login, totem, painel, áudio | `src/services`, `contexts/`, `hooks/useAnnouncer`, `app/totem`, `app/panel` |
| 6 | Frontend: atendente e gestão; documentação e apresentação | `app/(attendant)`, `app/(manager)`, `docs/` |

## Plano (25 dias)

| Semana | Entregas | Critério de pronto |
|---|---|---|
| 1 (dias 1–5) | Estrutura, Docker/MySQL, modelos + migration, JWT, contratos da API (OpenAPI) | `flask db upgrade` ok; login testado; Swagger publicado |
| 2 (6–10) | Emissão, QueueService, máquina de estados, serviços HTTP do frontend | Testes de concorrência e de prioridade verdes |
| 3 (11–15) | Atendimento, totem, painel, Socket.IO, áudio | Fluxo totem → atendente → painel funcionando ao vivo |
| 4 (16–20) | Gestão, relatórios, auditoria, segurança, tratamento de falhas | Relatórios conferidos contra o banco; testes de autorização |
| 5 (21–25) | Testes, correções, documentação, integração final, ensaio da apresentação | `docker compose up` em máquina limpa seguindo o README |

## Roteiro de apresentação sugerido

1. `docker compose up -d` e criação do administrador.
2. Gestor cria dois atendentes com guichês distintos.
3. Totem emite SG, SG, SE, SP, SP — mostrar códigos `YYMMDD-PPSQ`.
4. Dois atendentes chamam: painel exibe e anuncia na ordem SP → SE → SP → SG.
5. Repetir chamada ("Última chamada…") e registrar ausência.
6. Relatórios do dia, auditoria e encerramento do expediente.
7. Rodar `pytest` mostrando os testes de concorrência.
