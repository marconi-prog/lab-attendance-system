# Validação do alinhamento — 27/11/2026

Registro deste lote, separado dos resultados históricos de 23/11.

## Fontes e ambiente

- PDF da atividade (10 páginas) lido integralmente; especificação principal não localizada.
- Docker Desktop, imagem Python 3.14, MySQL 8.0 em contêiner e rede de revisão próprios.
- Banco exclusivo `attendance_conformidade_test`, descartável, sem uso do banco da aplicação.
- Nenhum `.env` real foi usado como destino de testes. Segredos de revisão fora do repositório.
- Frontend preserva Expo/React Native Web. Previsões no painel preservadas conforme o solicitante.

## Resultados

| Verificação | Resultado |
|---|---|
| Build do backend com Python 3.14 | Passou; runtime observado 3.14.10, SQLAlchemy 2.0.44 e Pydantic 2.12.4 |
| Instalação de requirements-dev.txt + pip check em Python 3.14 | Passou, sem conflitos de dependências |
| Baseline anterior às alterações de gestor em Python 3.14/MySQL 8.0.46 | 235 testes passaram, exit code 0 |
| Migration MySQL com dois gestores ativos existentes | Recusou antes de DDL; contas, hashes e revisão Alembic preservados |
| Migration MySQL após resolução explícita do conflito no banco descartável | Passou; contas/hashes preservados; índice recusou segundo gestor e transação foi revertida |
| Links locais Markdown e estrutura das pastas | Conferidos sem destinos inexistentes; revisão independente corrigiu cardinalidade opcional de token_blocklist no MER |
| Suíte completa após implementação dos perfis | 289 testes passaram em Python 3.14/MySQL 8.0.46 e SQLite |
| Regressão de chamada após revogação, desativação ou encerramento | Antes: 3 falhas esperadas (DID NOT RAISE); depois: 3 testes passaram em MySQL separado |
| Suíte completa final após revisão da concorrência | **292 testes passaram em 500,95 s**, exit code 0; `python -m pytest tests tests_isolated -o addopts= -q` |
| Frontend Windows / Node 24.18.0 | `npm ci --no-audit --no-fund` (812 pacotes), `npm run typecheck` e `npm run lint` passaram, exit code 0 |
| Revisão técnica independente | Sem bloqueadores após corrigir concorrência de revogação; validação de sessão ocorre na transação, com ordem Counter → QueueState → Ticket |
| Build web no Docker / Node 22 | Passou, exportação estática completa com `expo export --platform web --max-workers 2` |
| Compose em projeto/volume novos | Build passou; MySQL, backend e frontend saudáveis; migrations aplicadas no banco novo |
| Interface do gestor no navegador | Login, edição do próprio usuário e autorização no guichê 01, alternância Gestão/Atendimento, abertura do guichê, emissão SP no totem, chamada/início/fim pelo gestor passaram |
| Indicadores e encerramento da sessão | Gestão exibiu 1 emitida e 1 atendida, guichê mantido ao alternar áreas; saída liberou o guichê e logout retornou ao login; zero erros no console capturado |

O build web foi limitado a dois workers para reduzir pressão de memória no equipamento de 8 GB;
a suíte final foi concluída antes de retomá-lo. A validação de interface foi guiada via automação
do navegador, sem suíte E2E versionada. O áudio não foi revalidado neste lote, que não o alterou.

Projeto Docker de revisão: `lab-conformidade-compose-20261127`; frontend em loopback 18082,
backend 15002 e MySQL 13382. O banco de testes automatizados e o de migrations são distintos
do banco desse Compose e de qualquer banco da aplicação anterior. Nenhum volume anterior foi apagado.

## Pendências externas

- Quatro colaboradores: depende do administrador Marconi e da aceitação dos convites.
- PDF principal: falta confirmar horário de emissão e regra dos aproximadamente 5% de ausências.
- Datas, inscrição, Teams e apresentação: sob responsabilidade do solicitante.
- Confirmação de áudio em 23/11 foi real, mas não substitui verificação no equipamento da apresentação.
