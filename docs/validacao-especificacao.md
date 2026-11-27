# Validação complementar dos PDFs — 27/11/2026

Especificação principal versão06 e edital de backend (8 páginas cada), recebidos após o lote do
PR#4, lidos integralmente. Esta revisão complementa os [292 testes anteriores](validacao-conformidade.md).
Os hashes e requisitos constam em [requirements/README.md](requirements/README.md).

## Evidências deste lote

| Verificação | Resultado |
|---|---|
| Regressões de horário/API v1 antes da implementação | 8 falhas esperadas, 12 aprovações |
| Horário 07h–17h, configuração legada, API v1 e OpenAPI após correção | 25 testes aprovados em Python3.14/MySQL8 descartável |
| Backup e restauração em banco novo | Dados e caracteres UTF-8 idênticos por SHA-256; origem preservada |
| Restauração sobre destino já existente | Recusada com exit2; sem alterações |
| Backup/restauração do esquema completo | 12 tabelas da aplicação e uma tabela de controle (13 ao todo); usuário e permissão sintéticos, hash e coluna calculada de gestor preservados |
| Origem usada como destino | Recusada antes de qualquer alteração |
| Isolados do simulador e relatório (Claude) | 153 testes passaram em Python3.12/SQLite temporário; sem MySQL |
| Fronteira do simulador: finalizar após17h | Regressão reproduzida antes da correção; novas chamadas limitadas ao expediente, término posterior permitido e ocupação com horizonte explícito |
| Suíte completa final | **387 testes passaram em 178,90s**, Python3.14.10/MySQL8.0.46 e SQLite; `python -m pytest tests tests_isolated -o addopts= -q` |
| Imagem final do backend | Build passou com Python3.14; dependências preservadas |
| CLI real no Docker com `--network none` | Rodou com endereço MySQL propositalmente inexistente:100 emitidas,95 atendidas,5 ausências,0 descartes de encerramento |
| Reprodutibilidade CLI | Mesmo seed42/data2026-11-27 produziu JSON com SHA-256 idêntico em dois processos separados |
| Proteção CLI em produção | Recusou com mensagem explícita, sem acesso ao banco |
| Revisão independente | Sem bloqueadores; consistência final entre simulador, encerramento, indicadores e documentação confirmada |

Testes executados em banco exclusivo `attendance_spec_test`, descartável. Backup/restauração
usaram outros bancos exclusivos com dados sintéticos. Nenhum banco ou conta real foi alterado.
Os links locais foram conferidos e `git diff --check` passou. Frontend não foi alterado;
a validação de interface do lote anterior permanece datada, e o CI também verifica o frontend.

O atendimento real não recebe quotas de descarte nem durações inventadas. O simulador acadêmico
produz cenários sintéticos, com indicador explícito de simulação e sem acessar os dados reais.
Não houve alterações de frontend neste lote; a API antiga permanece compatível.

## Pendências que dependem de pessoas

- Marconi convidar os quatro integrantes restantes; os integrantes precisam aceitar.
- Karllyson, Gustavo e Janildo realizar contribuições reais e identificáveis no Git.
- Todos estudar o código e participar da apresentação/arguição; inscrição e entrega Teams são da equipe.
- Novas tags não modificam datas nem tornam retroativos os commits posteriores ao prazo do edital.
