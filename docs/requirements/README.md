# Requisitos e regras de negócio

Fonte conferida: **Atividade — Sistema para controle de atendimento.pdf**, 10 páginas,
fornecido pelo solicitante em 27/11/2026. O documento principal **Sistema para controle de
atendimento.pdf** não foi localizado; as dependências dele estão indicadas abaixo.
SHA-256 do PDF conferido: `2987f91979d1661791915ce71defbd8ed2ce2edc8afa9ec7f3edcbe76919f9a1`.
Rastreabilidade de código/testes em [`requirements.md`](../requirements.md), arquitetura em
[`architecture.md`](../architecture.md), situação verificada em [`conformidade.md`](../conformidade.md).

## Funcionais

| ID | Requisito | Referência |
|---|---|---|
| RF01 | Emissão anônima no totem de SP, SE e SG | pp. 3–4 e 6 |
| RF02 | Código YYMMDD-PPSQ, sequência de três dígitos por categoria/dia | p. 4 |
| RF03 | Alternância SP → SE/SG → SP; após SP, SE antes de SG; filas vazias não bloqueiam | p. 4 |
| RF04 | Chamar, iniciar, finalizar, repetir uma vez e registrar ausência após duas chamadas | pp. 4–5 |
| RF05 | Estados emitida, aguardando, chamada, chamada novamente, em atendimento, atendida e não compareceu | p. 5 |
| RF06 | Qualquer categoria em qualquer guichê; operação depende de autorização do usuário | p. 4 |
| RF07 | Cinco últimas senhas chamadas; voz com prioridade, senha e guichê; repetição com Última chamada | pp. 5–6 |
| RF08 | Relatórios diário/mensal: totais e por categoria, detalhes, tempos médios e auditoria | pp. 5–6 |
| RF09 | Auditoria: atendente, guichê, senha, chamadas, início e finalização | p. 6 |
| RF10 | Login da equipe e um atendente com perfil adicional de gestor | p. 6 |
| RF11 | Cadastros e relatórios para gestor; cliente anônimo | p. 6 |
| RF12 | Expediente 07h–17h; concluir atendimentos iniciados; descartar senhas ainda aguardando | p. 4 |

## Permissões

| Operação | Anônimo | Atendente | Gestor |
|---|---|---|---|
| Emitir / visualizar painel público | Sim | Sim | Sim |
| Operar guichê autorizado | Não | Sim | Sim |
| Operar guichê não autorizado | Não | Não | Não |
| Cadastros, relatórios e auditoria administrativa | Não | Não | Sim |

Somente um gestor ativo é permitido. Contas históricas não são apagadas para alcançar esse limite.
Migração de base com múltiplos gestores ativos exige resolução administrativa explícita.

## Não funcionais e operação

| Tema | Requisito / implementação e limite |
|---|---|
| Segurança | JWT, refresh/revogação, hash scrypt, validação de entrada, autorização consultada no banco; credenciais somente no ambiente |
| Concorrência | InnoDB, transações, bloqueio de sequência e fila, unicidade de código; gestor único protegido também no banco |
| Disponibilidade | Health checks, reconexão Socket.IO e comunicação de falhas; uma instância/worker, sem alta disponibilidade garantida |
| Desempenho | Índices da fila e relatórios, paginação, duração média e indicadores por atendente; sem SLA medido em produção |
| Auditoria | Histórico de transições e chamadas, ator e horários; acesso administrativo; não registrar senhas/tokens nos logs |
| LGPD | Totem anônimo e painel sem identificação pessoal do cliente; usuários da equipe contêm nome/e-mail e auditoria pode conter IP. Limitar acesso e cópias, definir prazo de retenção com responsável; não existe política automática de expurgo implementada |
| Acessibilidade | Categorias com sigla e texto além de cor, painel visual e sonoro; verificar teclado, leitores de tela, contraste e zoom no equipamento real. Não foi certificada conformidade integral WCAG |
| Falhas de infraestrutura | Falha de emissão não pode produzir confirmação falsa; avisar indisponibilidade e recuperar conexão; após timeout, conferir estado antes de repetir operação |
| Reprodutibilidade | Python 3.14, MySQL 8, React/Expo Web, Docker, migrations, instruções e testes de integração |

## Interpretações e exceções

- **Aceitos pelo solicitante:** React Native/Expo Web, nome `lab-attendance-system` e previsões no
  painel. A previsão diverge da p. 5; registrar aceitação do solicitante não equivale a evidência
  escrita de dispensa concedida pelo professor.
- **Horário de emissão:** configuração atual 06h–17h; chamadas 07h–17h, America/Recife. A atividade
  informa expediente 07h–17h. Preservado até conferência do PDF principal; não declarado conforme.
- **Aproximadamente 5% de ausências:** a p. 4 remete à especificação principal. O sistema permite
  ausência real após duas chamadas e contabiliza resultados. Não força ausências nem descarta
  clientes aleatoriamente. Falta determinar se o percentual é hipótese estatística ou simulação.
- **Final do expediente:** quem iniciou atendimento pode concluir; descarte é para aguardando,
  sem conversão automática de atendimento em andamento em abandono.
- **Agente Sistema (AS):** é a aplicação e infraestrutura, não o usuário gestor. A administração é
  uma capacidade adicional de um agente atendente.
