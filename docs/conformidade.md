# Matriz de conformidade

Situação em **23/11/2026**, preparada no lote inicial de preparação acadêmica (branch `dev`).

> **Limite desta matriz.** Os enunciados originais (PDFs) **não estão disponíveis** no repositório nem
> foram fornecidos nesta preparação. Os requisitos abaixo foram derivados de
> [`requirements.md`](requirements.md), [`architecture.md`](architecture.md) e do código e precisam ser
> conferidos contra os enunciados oficiais quando forem anexados.

## Evidências de validação registradas (23/11/2026)

| Validação | Ambiente | Resultado |
|---|---|---|
| Suíte existente `backend/tests/` | MySQL 8.0.46 descartável (`localhost:13379`, banco `attendance_validation_test`) | **196 testes passaram** em 243,68 s |
| Testes isolados `backend/tests_isolated/` | SQLite temporário | **39 testes passaram** em 48,10 s |
| Nova execução completa de `pytest` antes da integração | Mesmo MySQL descartável + SQLite temporário | **235 testes passaram** em 193,60 s |
| `flask db upgrade` | Outro banco descartável (`attendance_migration_test`) | Passou |
| `flask seed-demo` | MySQL descartável: `--dry-run` + 2 execuções reais | Passou; a 2ª execução preservou contas e senhas |
| `npm run typecheck` (frontend) | Contêiner Node 24 | Passou |
| Instalação limpa, TypeScript e lint finais | Contêiner Node 24, código corrigido e lockfile atualizado | `npm ci && npm run typecheck && npm run lint && npm run build:web` terminou com exit code 0, sem erros ou avisos de lint |
| Build web do frontend (`npm run build:web`) | Node 24; também build Docker com Node 22 | Passou; exportação `dist` gerada |
| Docker Compose | Projeto isolado `lab-attendance-review-20261123`, volume novo e portas em loopback | Build passou; MySQL, backend e frontend saudáveis; API health com banco OK e frontend HTTP 200 |
| Fluxo integrado no Docker | API em `127.0.0.1:15000`, frontend em `127.0.0.1:18080` | Gestor, cadastro/login de atendente, guichê, emissão SG/SE/SP, prioridade SP, início/fim, painel e relatório passaram |
| Interface (telas) | Navegador, telas de gestor, atendente, totem e painel | Fluxo guiado registrado em [`validacao-interface.md`](validacao-interface.md) |
| Áudio do painel | Navegador + confirmação do solicitante | Som habilitado, chamadas sem erros no console; solicitante confirmou sinal e voz |

As validações automáticas cobrem backend/API; as telas têm a verificação guiada separada acima.
O solicitante confirmou a reprodução do sinal e da voz durante o teste.

## Legenda

| Situação | Significado |
|---|---|
| Validado (backend/API) | Teste automatizado do backend executado e aprovado em 23/11/2026 |
| Implementado (manual) | Código existe; validação depende de teste manual ainda não registrado |
| Parcial | Atende em parte ou possui ressalva documentada |
| Pendente | Depende de ação ou informação |
| Sob responsabilidade do solicitante | Item que o solicitante declarou que vai tratar |

## 1. Requisitos funcionais

| # | Requisito | Evidência | Situação | Correção | Validação |
|---|---|---|---|---|---|
| F01 | Emissão SP/SE/SG, código `YYMMDD-PPSQ`, sequência diária por categoria, limite 999 | `ticket_service.py`, `daily_sequences`, `frontend/app/totem/index.tsx` | Backend/API e fluxo do totem verificados | Rolagem e cabeçalho em tela pequena corrigidos | `test_ticket_issuance.py` e roteiro guiado no navegador |
| F02 | Sem duplicidade com emissões simultâneas | `FOR UPDATE` + `UNIQUE(code)` | Validado (backend/API) | — | `test_concurrent_issuance_never_duplicates_codes` (aprovado) |
| F03 | Ciclo SP → SE/SG → SP; categorias vazias não bloqueiam | `QueueService.select_next_type` | Validado (backend/API) | — | `test_queue_policy.py`, `test_priority_cycle`, `test_cycle_handles_empty_categories` (aprovados) |
| F04 | Reserva atômica da próxima senha | `QueueService.call_next` | Validado (backend/API) | — | `test_concurrent_attendants_never_get_same_ticket`, `test_concurrent_double_click_reserves_only_one` (aprovados) |
| F05 | Máquina de estados com histórico imutável | `state_machine.py`, `ticket_status_history` | Validado (backend/API) | — | `test_state_machine.py` (aprovado) |
| F06 | Iniciar/finalizar atendimento com duração | `AttendanceService` | Validado (backend/API) | — | `test_start_and_finish` (aprovado) |
| F07 | Repetir chamada; ausência só após a 2ª chamada | `recall` + `no_show`; tabela `calls` | Validado (backend/API) | — | `test_recall_creates_new_call_record`, `test_third_call_is_not_allowed`, `test_no_show_after_two_calls_releases_queue` (aprovados) |
| F08 | Painel: chamada atual, 5 últimas, próximos, tempo real | `PanelService`, Socket.IO `/panel`, `frontend/app/panel/index.tsx` | Backend/API, eventos e atualização visual verificados | Fonte baseada na largura útil para não cortar o código | `test_panel_realtime.py` e roteiro guiado no navegador |
| F09 | Anúncio sonoro/voz no painel | `useAnnouncer.ts` (Web Audio + Expo Speech `pt-BR`) | Verificado no navegador e confirmado pelo solicitante | Som habilitado e chamadas sem erro no console | Solicitante confirmou ter ouvido sinal e voz; repetir no equipamento da apresentação |
| F10 | Expediente: chamadas 07–17h, emissão 06–17h, encerramento automático | `business_hours.py`, `day_closing_service.py`, `scheduler.py` | Validado (backend/API) | — | `test_business_hours`, `test_calls_blocked_outside_business_hours`, `test_day_closing_*`, `test_scheduled_closing*` (aprovados) |
| F11 | Atendente: guichê autorizado, chamar, repetir, iniciar, finalizar, ausência | `attendant_controller.py`, `frontend/app/(attendant)/attendant.tsx` | Backend/API e fluxo da interface verificados | — | `test_attendance.py` e roteiro guiado no navegador |
| F12 | Gestor: indicadores, usuários com guichês, guichês, relatórios, auditoria, encerrar dia | `user_service.py`, `counter_service.py`, `frontend/app/(manager)/manager/*` | Backend/API validados; telas de consulta verificadas | — | `test_management.py`, `test_dashboard` e consulta no navegador; encerramento validado por testes do backend |
| F13 | Relatórios diário, mensal e por período | `ReportService` | Validado (backend/API) | — | `test_reports.py` (aprovado) |
| F14 | Auditoria sem senhas | `AuditService` | Validado (backend/API) | — | `test_audit_log`, `test_login_is_audited_without_password` (aprovados) |

## 2. Segurança e API

| # | Requisito | Evidência | Situação | Correção | Validação |
|---|---|---|---|---|---|
| S01 | JWT access + refresh, revogação, hash de senha | `AuthService`, `middlewares/auth.py` | Validado (backend/API) | — | `test_refresh_flow`, `test_logout_revokes_tokens`, `test_deactivated_user_loses_access_immediately` (aprovados) |
| S02 | Autorização por perfil | `roles_required` via `api_route` | Validado (backend/API) | — | `test_anonymous_is_rejected`, `test_attendant_cannot_access_admin`, `test_admin_cannot_operate_counter` (aprovados) |
| S03 | Nenhuma credencial no código | `validate_config`, `.gitignore` | Implementado | — | Revisão de código; `.env` reais não foram lidos |
| S04 | OpenAPI/Swagger | `/api/docs`, `routes/registry.py` | Validado (backend/API) | — | `test_openapi.py` (aprovado) |

## 3. Infraestrutura, testes e documentação

| # | Requisito | Evidência | Situação | Correção | Validação |
|---|---|---|---|---|---|
| I01 | Flask + MySQL 8 com migrations Alembic | `0001_schema_inicial.py` | Validado | — | `flask db upgrade` aprovado em banco descartável `attendance_migration_test` |
| I02 | Docker Compose com health checks | `docker-compose.yml`, `.gitattributes`, `.dockerignore` | Validado em ambiente isolado local | Scripts `.sh` com LF e exclusão de dependências locais/arquivos de ambiente no build | Build, três serviços saudáveis, HTTP 200 e fluxo integrado via API |
| I03 | Frontend Expo (**aprovado**) | `package.json` (Expo SDK 58), `app.json`, `eslint.config.js` | Verificações estáticas, build e fluxo guiado da interface | Lint, Hooks, timer e legibilidade corrigidos | Instalação limpa, TypeScript, lint e build aprovados; ver `validacao-interface.md`; sem suíte E2E automatizada |
| I04 | Nome do projeto (**aprovado**) | `README.md`, `app.json` | Implementado | — | — |
| I05 | Testes executáveis com segurança | `backend/tests/` (MySQL), `backend/tests_isolated/` (SQLite) | Validado | README corrigido: `tests/` inteira (inclusive `tests/unit`) apaga o banco de testes | 196 aprovados em MySQL descartável; 39 isolados aprovados |
| I06 | Dados de demonstração seguros | `backend/app/demo_seed.py` (`flask seed-demo`) | Validado | Comando novo (commit `7710003`) | 39 testes isolados aprovados; `--dry-run` + 2 execuções reais em MySQL, a 2ª preservando contas e senhas |
| I07 | README com PowerShell | `README.md` | Implementado | Revisado neste lote | Revisão humana |
| I08 | Fluxo `dev` → validação → PR → `main` | `README.md` §7 | Aguarda autenticação do Git | Publicação autorizada, mas `git push --dry-run` falhou por falta de login; commits locais preservados | Conector tem escrita, porém não transfere os commits locais com autoria/data originais |
| I09 | Tag da versão entregue | sem tags | Pendente após integração | `v1.0-entrega` deverá apontar para a versão integrada em `main` | — |
| I10 | Declaração de uso de IA | `README.md` §9 | Implementado | Histórico anterior a 23/11/2026 registrado como desconhecido | Revisão da equipe |
| I11 | Licença | `LICENSE`, `README.md` §11 | Implementado | MIT 2026 adicionada; copyright dos seis integrantes | — |
| I12 | Identificação da equipe | `README.md` §10, `entrega.md` §1 | Parcial | Nomes e matrículas preenchidos; nome oficial, GitHub de 4 integrantes e módulos pendentes | — |
| I13 | Datas | `entrega.md` §3 | Sob responsabilidade do solicitante | Registradas sem cobrança de confirmação | — |
| I14 | Enunciados originais | — | Pendente | Anexar PDFs ou links e reconferir a matriz | — |

## 4. Riscos observados (não corrigidos neste lote)

| Risco | Evidência | Recomendação |
|---|---|---|
| `FLASK_ENV` desconhecido cai na configuração de desenvolvimento (`DEBUG=True`) | `get_config` em `settings.py` | Avaliar falha explícita (decisão da equipe); o `seed-demo` já recusa valores ≠ `development` |
| `seed-demo` é recusado no Docker Compose (`FLASK_ENV=production`) | `docker-compose.yml` | Intencional; no Docker usar `create-admin` + cadastro pela interface |
| SE tem preferência sobre SG após SP | `architecture.md` | Já documentado; decisão de negócio |
| Socket.IO em 1 worker; sem rate limit no totem; tokens em `sessionStorage` | `architecture.md` | Já documentado |
