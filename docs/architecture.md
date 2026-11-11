# Arquitetura

## Visão geral

```text
 ┌──────────── Frontend (Expo / React Native Web) ────────────┐
 │  /totem   /panel   /login   /attendant   /manager/*         │
 │  Axios (REST + refresh automático)  ·  Socket.IO client     │
 └───────────────┬─────────────────────────────┬───────────────┘
                 │ HTTPS/JSON                  │ WebSocket
 ┌───────────────▼─────────────────────────────▼───────────────┐
 │ Flask  ── routes (registry) ── controllers ── services ──┐   │
 │   middlewares: JWT, perfis, validação Pydantic, erros     │   │
 │   sockets: /panel (público, leitura) · /staff (JWT)       │   │
 │   scheduler: encerramento automático do expediente        │   │
 │                                   repositories ── models ─┘   │
 └───────────────────────────────┬──────────────────────────────┘
                                 │ SQLAlchemy 2 / PyMySQL
                        ┌────────▼────────┐
                        │   MySQL 8 InnoDB │
                        └─────────────────┘
```

## Backend — camadas

| Camada | Responsabilidade | Exemplos |
|---|---|---|
| `routes/` | Declara URL, método, perfis permitidos e schemas. O `api_route` aplica auth + validação e alimenta o OpenAPI. | `routes/__init__.py`, `routes/registry.py` |
| `controllers/` | Adaptam HTTP ↔ serviço; não contêm regra de negócio. | `attendant_controller.py` |
| `services/` | Regras de negócio e transações. | `QueueService`, `TicketService`, `AttendanceService`, `TicketStateMachine`, `ReportService` |
| `repositories/` | Consultas SQLAlchemy, incluindo leituras com bloqueio (`FOR UPDATE`, `SKIP LOCKED`). | `TicketRepository` |
| `models/` | Entidades ORM, enums, constraints e índices. | `Ticket`, `Call`, `Attendance` |
| `schemas/` | Pydantic: entrada (`extra="forbid"`) e saída (datas no fuso America/Recife). | `TicketCreate`, `TicketOut` |
| `middlewares/` | Erros centralizados, callbacks JWT, autorização por perfil, cabeçalhos de segurança, log de acesso. | |
| `sockets/` | Namespaces Socket.IO. | `PanelNamespace`, `StaffNamespace` |

### Decisões principais

1. **Atomicidade da emissão.** A sequência diária fica em `daily_sequences` (única por data+categoria).
   A linha é criada por `INSERT IGNORE` numa transação curta e depois bloqueada com `SELECT … FOR UPDATE`
   na transação da emissão. Isso serializa emissões da mesma categoria sem gap locks/deadlocks; a
   `UNIQUE(code)` em `tickets` é a última barreira. Testado com 40 emissões simultâneas.
2. **Atomicidade da chamada.** `QueueService.call_next` bloqueia a linha do dia em `queue_states`
   (guarda o último tipo chamado) — serializa as chamadas entre guichês, garantindo que ninguém
   receba a mesma senha **e** que o ciclo SP → SE/SG → SP seja respeitado globalmente. A senha é lida
   com `FOR UPDATE SKIP LOCKED`. A verificação de "guichê ocupado" acontece **após** o bloqueio, o que
   neutraliza duplo clique. Testado com 10 guichês simultâneos.
3. **Regra de prioridade isolada.** `QueueService.select_next_type(last, waiting)` é função pura
   (testada sem banco); o restante do serviço só aplica o resultado.
4. **Máquina de estados única.** Toda mudança de status passa por `TicketStateMachine.transition`,
   que valida a tabela de transições e grava `ticket_status_history` (quem, quando, qual guichê).
5. **Eventos só após commit.** `RealtimeNotifier` é chamado depois de `run_in_transaction` — o painel
   nunca mostra senha não chamada. Clientes não emitem eventos de estado.
6. **Datas em UTC no banco**, regras e respostas em America/Recife (`utils/clock.py`). O relógio é
   substituível nos testes (`Clock.now_utc`).
7. **Deadlock/lock timeout** (MySQL 1213/1205) são repetidos automaticamente em `run_in_transaction`.
8. **Isolamento READ COMMITTED** para que leituras bloqueantes vejam sempre o último valor confirmado.
9. **OpenAPI gerado do código**: o mesmo registro que monta as rotas monta `/api/docs/openapi.json`.

### Tempo real

| Namespace | Acesso | Eventos recebidos |
|---|---|---|
| `/panel` | público, somente leitura (`panel:sync` devolve o estado) | `ticket:called`, `ticket:recalled`, `panel:updated` |
| `/staff` | JWT de acesso em `auth.token`; token revogado/usuário inativo é recusado | `ticket:issued`, `ticket:called`, `ticket:recalled`, `ticket:updated`, `attendance:started`, `attendance:finished`, `queue:updated` |

A origem (`Origin`) do handshake é validada contra `CORS_ORIGINS`. Em produção roda com Gunicorn
(1 worker, N threads); para mais de um worker/servidor seria necessário um `message_queue` (Redis).

### Expediente

* Chamadas: 07:00–17:00 (America/Recife). Emissão: 06:00–17:00.
* Às 17:00 o agendador (thread a cada 60 s) descarta as senhas `AGUARDANDO` do dia e marca o dia como
  encerrado; também descarta pendências de dias anteriores. Senhas já chamadas/em atendimento podem ser
  concluídas (iniciar, finalizar, repetir e registrar ausência continuam permitidos).
* `ENFORCE_BUSINESS_HOURS=false` desativa o bloqueio (demonstrações). O gestor pode encerrar o dia
  manualmente (`POST /api/admin/close-day` ou `flask close-day`).

## Frontend

* **Expo Router** com grupos: `(auth)/login`, `(attendant)/attendant`, `(manager)/manager/*`, `totem`, `panel`.
  `RoleGuard` protege os grupos por perfil.
* **Serviços** (`src/services`): `authService`, `ticketService`, `attendanceService`, `panelService`,
  `reportService`, `userService`, `counterService` sobre um Axios com renovação automática do token e
  normalização de erros (`ApiError`).
* **TanStack Query** para cache/requisições; `useStaffSocket` invalida as queries quando o servidor
  notifica mudanças. O painel aplica `panel:updated` diretamente no cache.
* **AuthContext** guarda o usuário; tokens em `expo-secure-store` (nativo) ou `sessionStorage` (web).
* **Áudio** (`useAnnouncer`): fila de anúncios, sinal sonoro via Web Audio API + voz via Expo Speech
  (`pt-BR`). No navegador, o painel pede um clique para liberar áudio; sem síntese de voz, toca o sinal.
* Formulários com React Hook Form + Zod; ícones Lucide.

## Riscos e conflitos técnicos identificados

| Risco | Mitigação |
|---|---|
| Duplicidade de senha/chamada sob concorrência | Bloqueios InnoDB + unique constraints + testes multi-thread |
| Starvation de SG quando há muitas SE (regra literal: SE tem preferência após SP) | Documentado; se o laboratório preferir, alternar SE/SG é uma mudança só em `select_next_type` |
| Autoplay de áudio bloqueado pelo navegador | Botão "Ativar som" no painel; sinal sonoro como alternativa |
| Fuso horário (servidor UTC × regras locais) | UTC no banco, conversão centralizada, testes com relógio congelado |
| Sessão de guichê "presa" (navegador fechado) | Gestor encerra a sessão; senha em andamento continua vinculada ao guichê |
| Escala horizontal do Socket.IO | 1 worker com threads; Redis como `message_queue` para escalar |
| Endpoint público do totem pode ser abusado | Limite diário de 999 por categoria; recomenda-se rate limit no proxy (Nginx) em produção |
| Tokens no `sessionStorage` (web) expostos a XSS | Sem HTML dinâmico de terceiros; tokens curtos; revogação no logout |
