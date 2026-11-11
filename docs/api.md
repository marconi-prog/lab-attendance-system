# API REST

Base: `http://localhost:5000/api` · Swagger: `/api/docs` · OpenAPI JSON: `/api/docs/openapi.json`
(gerado do próprio código — sempre atualizado).

* JSON em UTF-8; corpos com campos desconhecidos são rejeitados (422).
* Autenticação: `Authorization: Bearer <access_token>`.
* Datas retornadas em ISO 8601 no fuso America/Recife (`2026-11-10T09:05:12-03:00`).
* Listas paginadas: `?page=1&per_page=20` → `{"items": [...], "meta": {"page","per_page","total","pages"}}`.

## Formato de erro

```json
{ "error": { "code": "QUEUE_EMPTY", "message": "Não há senhas aguardando atendimento.", "details": null } }
```

| HTTP | Códigos frequentes |
|---|---|
| 401 | `UNAUTHORIZED`, `INVALID_CREDENTIALS`, `TOKEN_EXPIRED`, `TOKEN_REVOKED`, `USER_INACTIVE` |
| 403 | `FORBIDDEN`, `COUNTER_NOT_AUTHORIZED`, `TICKET_NOT_OWNED` |
| 404 | `NOT_FOUND` |
| 409 | `COUNTER_BUSY`, `COUNTER_OCCUPIED`, `ACTIVE_TICKET_PENDING`, `EMAIL_IN_USE`, `COUNTER_NUMBER_IN_USE` |
| 422 | `VALIDATION_ERROR`, `INVALID_STATUS_TRANSITION`, `QUEUE_EMPTY`, `OUTSIDE_BUSINESS_HOURS`, `SECOND_CALL_REQUIRED`, `MAX_CALLS_REACHED`, `DAILY_LIMIT_REACHED`, `NO_COUNTER_SESSION`, `LAST_ADMIN`, `SELF_LOCKOUT` |
| 503 | `DATABASE_UNAVAILABLE` |

## Endpoints

| Método | Rota | Perfil | Descrição |
|---|---|---|---|
| GET | `/health` | público | Saúde da aplicação e do MySQL |
| GET | `/panel` | público | Últimas 5 senhas chamadas |
| POST | `/tickets` | público (totem) | Emitir senha `{type: SP\|SE\|SG}` |
| GET | `/tickets/types` | público | Categorias e se a emissão está aberta |
| GET | `/tickets` | ADMIN, ATTENDANT | Listar senhas (`date`, `status`, `type`) |
| GET | `/tickets/{id}` | ADMIN, ATTENDANT | Detalhe com chamadas, atendimento e histórico de estados |
| POST | `/auth/login` | público | Login → access + refresh token |
| POST | `/auth/refresh` | refresh token | Novo access token |
| POST | `/auth/logout` | autenticado | Revoga access (e refresh, se enviado) |
| GET | `/auth/me` | autenticado | Usuário atual |
| PUT | `/auth/password` | autenticado | Alterar a própria senha |
| GET | `/attendant/state` | ATTENDANT | Guichê, senha atual e resumo da fila |
| GET | `/attendant/counters` | ATTENDANT | Guichês autorizados e ocupação |
| POST | `/attendant/session` | ATTENDANT | Assumir guichê `{counter_id}` |
| DELETE | `/attendant/session` | ATTENDANT | Sair do guichê |
| POST | `/attendant/call-next` | ATTENDANT | Chamar próxima senha (QueueService) |
| POST | `/attendant/tickets/{id}/recall` | ATTENDANT | Repetir chamada (2ª e última) |
| POST | `/attendant/tickets/{id}/start` | ATTENDANT | Iniciar atendimento |
| POST | `/attendant/tickets/{id}/finish` | ATTENDANT | Finalizar atendimento |
| POST | `/attendant/tickets/{id}/no-show` | ATTENDANT | Não compareceu (após 2 chamadas) |
| GET/POST | `/users` | ADMIN | Listar (`search`, `role`, `active`) / criar |
| GET/PATCH | `/users/{id}` | ADMIN | Detalhar / atualizar (nome, e-mail, perfil, ativo, senha) |
| PUT | `/users/{id}/counters` | ADMIN | Definir guichês autorizados |
| GET | `/counters` | ADMIN, ATTENDANT | Listar guichês |
| POST | `/counters` | ADMIN | Criar guichê |
| PATCH | `/counters/{id}` | ADMIN | Atualizar / ativar / desativar |
| GET | `/counters/sessions` | ADMIN | Sessões abertas |
| DELETE | `/counters/sessions/{id}` | ADMIN | Encerrar sessão de guichê |
| GET | `/reports/summary` | ADMIN | Resumo por período (`start_date`, `end_date`, `type`) |
| GET | `/reports/daily` | ADMIN | Relatório do dia (`date`, `type`) + emissões por hora |
| GET | `/reports/monthly` | ADMIN | Relatório do mês (`month=YYYY-MM`, `type`) + por dia |
| GET | `/reports/attendances` | ADMIN | Histórico paginado (`start_date`, `end_date`, `type`, `status`) |
| GET | `/admin/dashboard` | ADMIN | Indicadores do dia |
| GET | `/admin/system` | ADMIN | Informações gerais do sistema |
| GET | `/admin/audit-logs` | ADMIN | Auditoria (`action`, `entity`, `user_id`, período) |
| POST | `/admin/close-day` | ADMIN | Encerrar expediente (descarta aguardando) |

## Exemplos

### Emitir senha (totem)
```http
POST /api/tickets
Content-Type: application/json

{"type": "SP"}
```
```json
201 Created
{
  "ticket": {
    "id": 2, "code": "261110-SP001", "short_code": "SP001", "type": "SP", "type_label": "Prioritária",
    "status": "AGUARDANDO", "status_label": "Aguardando", "daily_sequence": 1,
    "reference_date": "2026-11-10", "issued_at": "2026-11-10T09:02:11-03:00", "updated_at": "2026-11-10T09:02:11-03:00"
  },
  "waiting_ahead": 0
}
```

### Login
```http
POST /api/auth/login
{"email": "ana@laboratorio.com.br", "password": "********"}
```
```json
200 OK
{ "access_token": "eyJ…", "refresh_token": "eyJ…", "token_type": "Bearer",
  "user": { "id": 2, "name": "Ana", "email": "ana@laboratorio.com.br", "role": "ATTENDANT", "active": true,
            "counters": [{"id": 2, "name": "Guichê 02", "number": 2}], "created_at": "…", "updated_at": "…" } }
```

### Assumir guichê e chamar a próxima
```http
POST /api/attendant/session          {"counter_id": 2}          → 201
POST /api/attendant/call-next
```
```json
200 OK
{
  "ticket": { "id": 2, "code": "261110-SP001", "short_code": "SP001", "status": "CHAMADA", "...": "..." },
  "counter": { "id": 2, "name": "Guichê 02", "number": 2, "active": true, "created_at": "…" },
  "attempt_number": 1,
  "is_repeat": false,
  "called_at": "2026-11-10T09:05:00-03:00",
  "announcement": {
    "text": "Senha prioritária SP001, dirigir-se ao guichê 02.",
    "speech": "Senha prioritária S P 0 0 1, dirigir-se ao guichê 02."
  }
}
```
Fila vazia → `422 {"error": {"code": "QUEUE_EMPTY", …}}`. Guichê com senha em andamento → `409 COUNTER_BUSY`.

### Repetir chamada
`POST /api/attendant/tickets/2/recall` → `attempt_number: 2`, `is_repeat: true`,
`announcement.text: "Última chamada, senha prioritária SP001, guichê 02."`

### Iniciar / finalizar
```json
POST /api/attendant/tickets/2/finish → 200
{ "ticket": { "status": "ATENDIDA", "...": "..." },
  "attendance": { "id": 1, "started_at": "…T09:06:00-03:00", "finished_at": "…T09:10:30-03:00",
                  "duration_seconds": 270, "result": "CONCLUIDO", "user": {"id": 2, "name": "Ana"} } }
```

### Relatório resumido
`GET /api/reports/summary?start_date=2026-11-01&end_date=2026-11-30&type=SP`
```json
{
  "period": {"start_date": "2026-11-01", "end_date": "2026-11-30"}, "type": "SP",
  "totals": {"issued": 3, "attended": 2, "no_show": 1, "discarded": 0, "pending": 0, "not_attended": 1,
             "avg_attendance_seconds": 120.0, "avg_wait_seconds": 45.5},
  "by_type": [{"type": "SP", "label": "Prioritária", "issued": 3, "attended": 2, "...": "..."}],
  "by_status": {"ATENDIDA": 2, "NAO_COMPARECEU": 1, "...": 0},
  "by_attendant": [{"user_id": 2, "name": "Ana", "attended": 2, "avg_attendance_seconds": 120.0}],
  "by_counter": [{"counter_id": 2, "number": 2, "name": "Guichê 02", "attended": 2, "avg_attendance_seconds": 120.0}]
}
```

## Socket.IO

```js
import { io } from 'socket.io-client';
const panel = io('http://localhost:5000/panel');
panel.on('ticket:called', (call) => console.log(call.announcement.text));
panel.on('panel:updated', (snapshot) => render(snapshot.latest));

const staff = io('http://localhost:5000/staff', { auth: { token: accessToken } });
staff.on('queue:updated', (q) => console.log(q.waiting));
```
Payloads de `ticket:called`/`ticket:recalled` = resposta de `call-next`. `panel:updated` = resposta de `GET /api/panel`.
