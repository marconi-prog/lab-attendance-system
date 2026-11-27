# Simulação acadêmica de atendimento

O edital §5.1 (p. 2) exige tempos simulados por tipo e cerca de 5% de ausências. A especificação
principal pp. 4–6 descreve essas distribuições e a origem histórica dos 5%. Para não excluir clientes
reais nem inventar duração de serviços reais, o comando `flask simulate-attendance` produz somente
um cenário sintético em JSON, sem consultar/gravar banco, emitir eventos de rede ou aguardar tempo real.

## Distribuições

| Categoria | Duração sintética |
|---|---|
| SP | Uniforme de 10 a 20 minutos, em segundos |
| SG | Uniforme de 2 a 8 minutos, em segundos |
| SE | 60 segundos com probabilidade95%; 300 segundos com probabilidade5% |

Há cinco guichês sintéticos. O ciclo de prioridade reutiliza `QueueService.select_next_type` e a
numeração usa o formatador real. As ausências são sorteadas sem reposição, aproximadamente5%
do total; com100 senhas, são5. Uma ausência só se encerra após duas chamadas, sem atendimento.
Se houver senhas ainda aguardando no fechamento, elas são contabilizadas separadamente como
descartadas por encerramento, sem misturá-las ao percentual de não comparecimento.
Atendimentos já chamados podem terminar depois das17h; o simulador não antecipa descarte
usando conhecimento da duração futura de um atendimento.

Tempos médios, totais por tipo/guichê, chamadas, histórico de estados e auditoria do JSON são
**simulados**. A semente e a data tornam a execução reproduzível. Eles não alimentam os relatórios
da aplicação nem representam produtividade real de integrantes, atendentes ou clientes.
O percentual de ocupação usa a janela de simulação informada em `utilization_basis_seconds`,
estendida até a última conclusão quando um serviço ultrapassa o fechamento.

## Executar localmente

Com ambiente do backend instalado/configurado, `FLASK_ENV=development` e diretório `backend/`:

```powershell
flask simulate-attendance --confirm-demo --tickets 100 --seed 42 --date 2026-11-27
```

Limite de20 a300 senhas; padrões100 e semente42. Sem `--date`, usa a data local. Produção,
ambiente desconhecido e ausência de `--confirm-demo` são recusados. O comando não pede senha nem
cria usuários. A saída padrão é JSON; o chamador pode armazená-la em pasta de revisão, fora do Git.

## Executar com a imagem Docker sem migrations ou seed

Na raiz, com o `.env` do Compose configurado:

```powershell
docker compose run --rm --no-deps --entrypoint flask -e FLASK_ENV=development backend simulate-attendance --confirm-demo --tickets 100 --seed 42 --date 2026-11-27
```

O `--entrypoint flask` é intencional: evita executar o entrypoint normal, que aplica migrations e
seed do serviço. `--no-deps` evita subir o MySQL. Não se deve desabilitar proteções do serviço
de produção para demonstrar a simulação; o comando acima roda em um processo descartável separado.

Os atendimentos reais continuam usando os botões da interface e duração medida entre início e fim;
não há quota automática de clientes descartados, alteração do relógio global ou espera artificial.
