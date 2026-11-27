# Matriz de conformidade

Conferência em **27/11/2026**: atividade (10 páginas), especificação principal versão06 (8 páginas)
e edital completo de backend (8 páginas), todos lidos integralmente. A matriz abaixo incorpora os
requisitos encontrados; resultados complementares em [validacao-especificacao.md](validacao-especificacao.md).

## Situação atual após a leitura da atividade

| Exigência | Fonte | Evidência / situação |
|---|---|---|
| Repositório público, MIT, .gitignore Node | pp. 1, 8–9 | GitHub público, `LICENSE` e `.gitignore` preservados |
| Nome nassauTickets | p. 1 | Nome existente aceito pelo solicitante; não renomeado |
| Seis membros, matrículas e papéis | pp. 1–2, 8 | Seção exata `## Membros` no README; Marconi é o único Scrum Master |
| Todos como colaboradores | pp. 1–2 | **Pendente externo:** API autenticada em 27/11 confirma somente Marconi e Sérgio; faltam os outros quatro |
| Histórico de todos os integrantes | Edital p. 7 | **Pendente externo:** três pessoas identificadas como autores (Marconi, Sérgio e Pedro). Karllyson, Gustavo e Janildo precisam realizar contribuições reais; papéis atribuídos não substituem commits |
| Estrutura obrigatória | pp. 2–3 | `backend/`, `frontend/`, `docs/{branding,mer,mockups,models/uml,requirements}` com artefatos; sem .gitkeep desnecessário |
| Documentação e artefatos | p. 3 | MER/UML em Mermaid, wireframes HTML, identidade e catálogo de requisitos derivados do código |
| Segurança, disponibilidade, LGPD e acessibilidade | p. 3 | `requirements/README.md` explicita implementação e limites; sem SLA ou certificação inventados |
| Agentes AS, AA e AC | pp. 3–4 | AS é aplicação/infraestrutura; AA é atendente, com gestor adicional; AC é anônimo |
| Tipos, numeração e prioridade | p. 4 | `TicketService`, `QueueService`; sequência por dia/categoria e bloqueios InnoDB |
| Duas chamadas e estados | pp. 4–5 | `TicketStateMachine`, `recall`, `no_show`; ausência após segunda chamada |
| Tempos simulados e aproximadamente 5% não atendidas | Principal pp. 4–6; edital p. 2 | Simulação acadêmica sintética separada; atendimento real mede duração e confirma ausência após duas chamadas, sem descarte aleatório |
| Expediente e encerramento | Atividade p. 4; edital p. 2 | Emissão e chamadas 07h–17h; configuração legada 06h não antecipa abertura; encerramento descarta aguardando e permite concluir serviços iniciados |
| Cinco últimas chamadas | p. 5 | `PanelService.latest`, limite 5 |
| Não mostrar próxima senha | p. 5 | **Exceção aceita pelo solicitante:** previsões mantidas; sem registro escrito de dispensa pelo professor |
| Relatórios e auditoria | pp. 5–6 | `ReportService`, chamadas, atendente, guichê, início/fim e agregações |
| Detalhes de senhas não atendidas | Principal p. 7 | Campos de atendimento ficam nulos; chamadas continuam auditáveis |
| API REST versionada | Rubrica do edital p. 6 | Prefixo `/api/v1`, aliases `/api` compatíveis e OpenAPI com IDs de operação únicos |
| Recuperação e backup | Principal p. 8; edital p. 3 | `docs/recuperacao.md`, scripts de backup/restauração em banco novo, teste de dados/UTF-8 e recusa de sobrescrita |
| Casos de uso, estados, classes/MER e sequência | Principal p. 8; edital p. 4 | `docs/models/uml/casos-de-uso.md`, UML e MER |
| Atendente com perfil adicional de gestor | p. 6 | ADMIN acumula atendimento autorizado e administração; um gestor ativo com proteção no banco e migration que preserva contas |
| Concorrência, métricas, voz e última chamada | p. 6 | Bloqueios, relatórios por atendente e `build_announcement`; áudio confirmado historicamente em 23/11 |
| Falhas de backend/banco | p. 6 | Erros normalizados, falha/reconexão na interface; limites em requisitos |
| React | pp. 6–8 | Expo/React Native Web aceito pelo solicitante; código em `frontend/` |
| Python 3.14/Flask, MySQL 8 | pp. 6–7 | Dockerfile e CI 3.14, `.python-version`; Flask justificado no README; execução registrada separadamente |
| main/dev e merge | p. 7 | PR #1 registra dev → main. PR #2 de outra branch → main é desvio histórico; sem reescrever commits. Este lote segue dev → main |
| README, configuração e testes | p. 8 | Instruções locais/Docker, migrations, demo, arquitetura, membros e papéis |
| Entrega Teams, datas e apresentação | pp. 9–10 | Responsabilidade do solicitante; não enviadas automaticamente |

### Evidência atual e dependências

Resultados deste lote: [validacao-conformidade.md](validacao-conformidade.md).
Consulta de colaboradores em 27/11: `marconi-prog` (admin) e `DevNeto07` (write).
Pedro contribuiu como `Pedro_HenriRod`, pela PR #2 da conta `Subaru21-bot`, mas não é colaborador
ativo. Marconi deve convidar os quatro restantes e eles devem aceitar; a conta autenticada não
tem administração. As contas de Karllyson, Gustavo e Janildo não foram inventadas.

Os prazos do edital não são alterados pelos novos commits ou tags: a avaliação considera a versão
existente no prazo aplicável (§6, p. 3). Inscrição, datas e envio no Teams continuam com o solicitante.
As exceções são aceites do solicitante, sem comprovação escrita do professor. A atribuição de
papéis não foi usada para inventar contribuições anteriores. A tag publicada `v1.0-entrega`
permanece preservada e não representa automaticamente alterações posteriores.

## Histórico anterior — referência de 23/11/2026

As tabelas abaixo registram a situação **anterior** à leitura do PDF e às mudanças de 27/11.
Não substituem a matriz atual nem a nova execução dos testes. Em especial, a proibição anterior
de ADMIN operar guichê, a ausência de papéis e a indisponibilidade de todos os PDFs foram superadas.

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

## Limites atuais

- Socket.IO opera em um worker; escalar exige infraestrutura compartilhada (por exemplo, Redis).
- Totem não possui rate limit; tokens web usam sessionStorage; retenção LGPD não é automatizada.
- A suíte MySQL apaga o banco indicado em TEST_DATABASE_URL; usar somente banco descartável.
- seed-demo é intencionalmente recusado em produção; no Docker usar create-admin e cadastros da interface.
- A preferência de SE após SP pode atrasar SG; não foi alterada a regra literal da atividade.
- FLASK_ENV desconhecido ainda cai em configuração de desenvolvimento; não usar valor desconhecido.
