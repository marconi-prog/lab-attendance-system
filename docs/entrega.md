# Checklist de entrega

Situação em **23/11/2026**. Itens **pendentes** dependem da equipe; nada aqui foi inventado.
Conformidade técnica e evidências de validação: [`conformidade.md`](conformidade.md).

## 1. Identificação

| Item | Situação | Observação |
|---|---|---|
| Nome do projeto | **Aprovado** | "Sistema de Controle de Atendimento — Laboratório de Análises Clínicas" (repositório `lab-attendance-system`) |
| Tecnologia do frontend (Expo) | **Aprovado** | Expo SDK 58 / React Native + Web |
| Nome da equipe | Pendente | Identificação operacional: "Equipe lab-attendance-system" (**não** é nome oficial) |
| Integrantes (nome completo) | **Preenchido** | Informados pelo solicitante (tabela abaixo) |
| Matrículas | **Preenchido** | Informadas pelo solicitante, zeros à esquerda preservados |
| Colaboradores ativos no GitHub | **2 confirmados** | Consulta autenticada: `marconi-prog` (admin) e `DevNeto07` (write). Os outros quatro não aparecem na lista de ativos; convites pendentes não foram consultados |
| Inscrição da equipe | Pendente | Ver §3 (datas alternativas) |

| # | Nome | Matrícula | Usuário GitHub | Colaborador no repositório? | Módulo |
|---|---|---|---|---|---|
| 1 | Karllyson Paula | 01861379 | pendente | ☐ | a definir |
| 2 | Marconi Farias Araújo | 01783919 | `marconi-prog` | Sim — admin | a definir |
| 3 | Gustavo Buled Martins | 01797483 | pendente | ☐ | a definir |
| 4 | Sérgio Luiz dos Santos Neto | 01819969 | `DevNeto07` | Sim — write | a definir |
| 5 | Pedro Henrique Rodrigues da Silva | 01794091 | pendente | ☐ | a definir |
| 6 | Janildo Caluête de Farias Júnior | 01799458 | pendente | ☐ | a definir |

A ordem da tabela não indica divisão de módulos; os módulos previstos em `requirements.md` (Dev 1–6)
ainda não foram atribuídos a integrantes.
Marconi deve conferir/adicionar Karllyson, Gustavo, Pedro e Janildo usando seus usuários GitHub reais;
o solicitante atual possui escrita, mas não administração para gerenciar esses convites.

## 2. URLs

| Item | Valor | Situação |
|---|---|---|
| Repositório | https://github.com/marconi-prog/lab-attendance-system | Confirmado pelo `git remote` |
| Pull request `dev` → `main` | https://github.com/marconi-prog/lab-attendance-system/pull/1 | Registro da integração; consultar o estado e SHA no próprio PR |
| Tag/release da entrega | `v1.0-entrega` | Referência da entrega, criada somente sobre a versão integrada; conferir em https://github.com/marconi-prog/lab-attendance-system/tags |
| Demonstração online | — | Inexistente: demonstração prevista é local |
| Vídeo ou slides | — | Pendente (se exigido) |
| Swagger | `http://localhost:5000/api/docs` | Apenas local |

## 3. Datas (sob responsabilidade do solicitante)

O solicitante declarou que cuidará das datas. Registro das informações recebidas:

| Item | Data informada | Observação |
|---|---|---|
| Frontend | 25/11/2026 | — |
| Backend | 13/11/2026 ou 27/11/2026 | Datas **alternativas de inscrição**, não necessariamente conflitantes; envio no dia anterior à data escolhida |
| Interface | 28/11/2026 | — |

## 4. Repositório: `dev`, `main` e tag

O trabalho foi desenvolvido e publicado na `dev`, preservando os commits por lote e sua autoria:
`DevNeto07 <sergiunetu@gmail.com>`, confirmada pelo solicitante. A integração é rastreada pelo
[PR #1](https://github.com/marconi-prog/lab-attendance-system/pull/1), que é a fonte para conferir o estado
do merge e seu SHA. A tag `v1.0-entrega` identifica a versão de entrega e deve apontar para a versão
integrada em `main`. Nenhuma alteração foi atribuída artificialmente aos demais integrantes.

- [x] Revisar e organizar as correções locais em commits por lote na `dev`
- [x] Publicar a `dev` no remoto
- [x] Abrir o PR `dev` → `main` com as evidências de validação
- [x] Revisão técnica e verificações pelo Codex, com implementação assistida pelo Claude Code
- [ ] Antes do envio acadêmico, conferir no GitHub o PR #1 mesclado e a tag `v1.0-entrega`
- [ ] Revisão adicional de outro integrante e conferência dos colaboradores ativos

## 5. Validação

- [x] `pytest` em `backend/tests/` — 196 aprovados em MySQL 8.0.46 descartável (243,68 s)
- [x] `pytest tests_isolated` — 39 aprovados em SQLite temporário (48,10 s)
- [x] Nova execução completa: **235 testes aprovados** em 193,60 s, nos bancos descartáveis de validação
- [x] `flask db upgrade` em banco descartável
- [x] `flask seed-demo` — `--dry-run` + 2 execuções reais em MySQL; a 2ª preservou contas e senhas
- [x] `npm run typecheck` — aprovado em contêiner Node 24
- [x] `npm ci` e `npm run lint` — instalação limpa e lint aprovados em Node 24
- [x] `npm run build:web` — aprovado em Node 24 e no build Docker (Node 22)
- [x] Docker Compose com volume/projeto de revisão novos — build aprovado e três serviços saudáveis
- [x] Smoke integrado via API no Docker — gestor, atendente, guichê, emissão, chamada, atendimento, painel e relatório
- [x] Fluxo guiado das telas de totem, atendente, gestor e painel — ver `validacao-interface.md`
- [x] Sinal e voz confirmados pelo solicitante durante as chamadas; repetir no equipamento da apresentação
- [ ] Conferir [`conformidade.md`](conformidade.md) contra os enunciados oficiais

## 6. Pendências documentais

| Pendência | Situação | Ação |
|---|---|---|
| Enunciados originais (PDFs) | Não disponíveis | Anexar ou registrar links; reconferir a matriz |
| Licença MIT | **Adicionada** (`LICENSE`, 2026, os seis integrantes) | — |
| Declaração de uso de IA | Redigida no README §9 | Equipe completar o histórico anterior a 23/11/2026 |
| Identificação da equipe | Integrantes e matrículas preenchidos | Pendentes: nome oficial da equipe, GitHub de 4 integrantes, módulos |

## 7. Roteiro de demonstração

**Ambiente local de desenvolvimento** (`backend/.env` com `FLASK_ENV=development`):

1. `flask db upgrade` e `flask seed` (guichês 01–05).
2. `flask seed-demo --dry-run` e `flask seed-demo --confirm-demo` (gestor e atendente com permissão no
   guichê 01; senhas digitadas no terminal). O comando **não** emite senhas de atendimento.
3. Totem (`/totem`): emitir SG, SG, SE, SP, SP — emissão das **06:00 às 17:00** (America/Recife).
4. Atendente: login, escolher o guichê, **Chamar próxima** — chamadas das **07:00 às 17:00**. Painel
   (`/panel`, clique para liberar o áudio) anuncia na ordem SP → SE → SP → SG.
5. Repetir chamada e registrar ausência.
6. Gestor: indicadores, relatórios, auditoria e encerramento do expediente.
7. Fora do horário: somente em demonstração, `ENFORCE_BUSINESS_HOURS=false` e reiniciar o backend.

**Docker Compose**: o backend roda com `FLASK_ENV=production`, então o `seed-demo` é recusado. Use
`docker compose exec backend flask create-admin ...` e cadastre o atendente pela área do gestor.
