# Checklist de entrega

Situação em **27/11/2026**. Itens pendentes são explicitados; papéis atribuídos não representam
contribuições anteriores inventadas. Resultados antigos permanecem datados como históricos.
Conformidade técnica e evidências de validação: [`conformidade.md`](conformidade.md).

## 1. Identificação

| Item | Situação | Observação |
|---|---|---|
| Nome do projeto | **Aprovado** | "Sistema de Controle de Atendimento — Laboratório de Análises Clínicas" (repositório `lab-attendance-system`) |
| Tecnologia do frontend (Expo) | **Aprovado** | Expo SDK 58 / React Native + Web |
| Nome da equipe | **Preenchido** | Nassau Ticket, conforme README atualizado pela equipe |
| Integrantes (nome completo) | **Preenchido** | Informados pelo solicitante (tabela abaixo) |
| Matrículas | **Preenchido** | Informadas pelo solicitante, zeros à esquerda preservados |
| Colaboradores ativos no GitHub | **2 confirmados em 27/11** | Consulta autenticada: `marconi-prog` (admin) e `DevNeto07` (write). Os outros quatro não aparecem na lista de ativos; convites pendentes não foram consultados |
| Inscrição da equipe | Pendente | Ver §3 (datas alternativas) |

| # | Nome | Matrícula | Usuário GitHub | Colaborador no repositório? | Módulo |
|---|---|---|---|---|---|
| 1 | Karllyson Paula | 01861379 | pendente | ☐ | Testes e validação |
| 2 | Marconi Farias Araújo | 01783919 | `marconi-prog` | Sim — admin | Coordenação (Scrum Master) e desenvolvimento |
| 3 | Gustavo Buled Martins | 01797483 | pendente | ☐ | Desenvolvimento |
| 4 | Sérgio Luiz dos Santos Neto | 01819969 | `DevNeto07` | Sim — write | Desenvolvimento, correções e testes |
| 5 | Pedro Henrique Rodrigues da Silva | 01794091 | `Subaru21-bot` (autor Git: `Pedro_HenriRod`) | Não consta como colaborador ativo | Documentação |
| 6 | Janildo Caluête de Farias Júnior | 01799458 | pendente | ☐ | Documentação |

Atribuição de papéis em 27/11/2026, autorizada pelo solicitante e detalhada na seção `## Membros`
do README. Marconi, Sérgio e Pedro têm contribuições identificadas no histórico. Os papéis dos
demais indicam responsabilidades a assumir; não comprovam trabalho anterior. A divisão dos seis
módulos sugeridos em `requirements.md` continua independente desta atribuição de papéis.

O checklist do edital (p. 7) pede histórico de todos os integrantes. Há contribuições identificadas
de Marconi, Sérgio e Pedro; Karllyson, Gustavo e Janildo ainda precisam contribuir de verdade com
documentação, código ou testes e fazer seus próprios commits. Não alterar autores nem inventar histórico.
Marconi deve conferir/adicionar Karllyson, Gustavo, Pedro e Janildo usando seus usuários GitHub reais;
o solicitante atual possui escrita, mas não administração para gerenciar esses convites.

**Ação do administrador:** GitHub → Settings → Collaborators → Add people. Convidar Pedro pela
conta da PR #2 (`Subaru21-bot`), confirmar com Karllyson/Gustavo/Janildo suas contas e convidá-los
com acesso de escrita. Cada integrante precisa aceitar. Conferir os seis na lista de acesso;
histórico de commits/PRs, sozinho, não comprova participação como membro do repositório.

## 2. URLs

| Item | Valor | Situação |
|---|---|---|
| Repositório | https://github.com/marconi-prog/lab-attendance-system | Confirmado pelo `git remote` |
| Pull request `dev` → `main` | https://github.com/marconi-prog/lab-attendance-system/pull/1 | Registro da integração; consultar o estado e SHA no próprio PR |
| Pull request do alinhamento ao PDF | https://github.com/marconi-prog/lab-attendance-system/pull/4 | Fonte do estado do merge, SHA e verificações deste lote |
| Tag/release anterior | `v1.0-entrega` | Preservada em `5764743`; não inclui mudanças posteriores. Não foi movida nem apresentada como a revisão final deste lote |
| Referência do alinhamento | `v1.0.1-entrega` | Publicar somente sobre a revisão integrada e validada; conferir existência e SHA na lista de tags |
| Complemento da especificação/edital | `v1.0.2-entrega` | Referência posterior, publicada somente após validação e integração; manter tags anteriores |
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
- [x] PR #1 mesclado; tag `v1.0-entrega` preservada em `5764743`
- [x] Publicar este lote pela dev e abrir [PR #4](https://github.com/marconi-prog/lab-attendance-system/pull/4); estado do merge e verificações consultáveis no próprio PR
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
- [x] Conferir [`conformidade.md`](conformidade.md) contra o PDF da atividade, 10 páginas
- [x] Ler especificação principal e edital de backend (8 páginas cada); emissão e chamadas 07h–17h; simulação separada do atendimento real

As verificações acima foram feitas em 23/11, antes das alterações de perfis/Python.
Resultados atuais ficam em [`validacao-conformidade.md`](validacao-conformidade.md).

## 6. Pendências documentais

| Pendência | Situação | Ação |
|---|---|---|
| PDF da atividade | **Lido (10 páginas)** | Estrutura, papéis e regras incorporados à matriz em 27/11 |
| Especificação principal e edital de backend | **Lidos integralmente** | Horários, simulação, campos em branco, recuperação, casos de uso e API versionada contemplados; ver `validacao-especificacao.md` |
| Licença MIT | **Adicionada** (`LICENSE`, 2026, os seis integrantes) | — |
| Declaração de uso de IA | Redigida no README §9 | Equipe completar o histórico anterior a 23/11/2026 |
| Identificação da equipe | Nome, integrantes, matrículas e papéis preenchidos | Confirmar contas de Karllyson/Gustavo/Janildo e acesso dos quatro restantes |
| Exceções aceitas pelo solicitante | Expo Web, nome do repositório, previsões no painel | Sem documento escrito de dispensa do professor para a previsão que diverge da p. 5 |

## 7. Roteiro de demonstração

**Ambiente local de desenvolvimento** (`backend/.env` com `FLASK_ENV=development`):

1. `flask db upgrade` e `flask seed` (guichês 01–05).
2. `flask seed-demo --dry-run` e `flask seed-demo --confirm-demo` (gestor e atendente com permissão no
   guichê 01; senhas digitadas no terminal). O comando **não** emite senhas de atendimento.
3. Totem (`/totem`): emitir SG, SG, SE, SP, SP — emissão das **07:00 às 17:00** (America/Recife).
4. Atendente: login, escolher o guichê, **Chamar próxima** — chamadas das **07:00 às 17:00**. Painel
   (`/panel`, clique para liberar o áudio) anuncia na ordem SP → SE → SP → SG.
5. Repetir chamada e registrar ausência.
6. Gestor: indicadores, relatórios, auditoria e encerramento do expediente.
7. Fora do horário: somente em demonstração, `ENFORCE_BUSINESS_HOURS=false` e reiniciar o backend.

**Docker Compose**: o backend roda com `FLASK_ENV=production`, então o `seed-demo` é recusado. Use
`docker compose exec backend flask create-admin ...` e cadastre o atendente pela área do gestor.
