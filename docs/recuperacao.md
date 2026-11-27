# Falhas, backup e recuperacao

Edital, secao 5.5 (p. 3) e especificacao principal (p. 8).

## Comportamento durante falhas

| Falha | API / persistencia | Frontend e painel |
|---|---|---|
| MySQL indisponivel | Health check falha; operacao retorna erro padronizado e nao confirma gravacao | Exibir indisponibilidade, permitir nova tentativa consciente; nao confirmar emissao ou atendimento sem resposta |
| Backend indisponivel | Sem confirmacao de comandos; Socket.IO desconecta | Indicacao de reconexao; ultimos dados sao historicos, nao prova de disponibilidade; recuperar snapshot apos reconectar |
| Timeout apos comando | Resultado pode ter sido confirmado antes de perder a resposta | Consultar estado atual antes de repetir; duplicidade de chamada e bloqueada por guiche ocupado, mas emissao nao tem chave de idempotencia |
| Processo reiniciado | Compose usa restart e health checks; migrations na inicializacao | Reautenticar se necessario, recuperar sessao de guiche e estado persistido; nao avancar fila localmente |

Nao ha failover automatico, cache offline de escrita nem garantia de disponibilidade continua.
O sinal/voz depende do navegador e da interacao inicial; reconectar nao dispensa conferir o audio.

## Backup logico (PowerShell 7)

Executar na raiz do repositorio, com o Compose configurado. As credenciais sao usadas somente
no ambiente do conteiner. O dump nao inclui CREATE DATABASE/USE: ele pode ser verificado em
outro banco. `--single-transaction` produz snapshot consistente das tabelas InnoDB; nao executar
alteracoes de schema durante a copia.

```powershell
New-Item -ItemType Directory -Force backups | Out-Null
docker compose cp database/operations/backup.sh mysql:/tmp/lab-backup.sh
$backupPath = Join-Path backups ("atendimento-" + (Get-Date -Format yyyyMMdd-HHmmss) + ".sql")
$backupSql = docker compose exec -T mysql sh /tmp/lab-backup.sh
if ($LASTEXITCODE -ne 0) { throw "Backup falhou; nao usar a saida parcial." }
$backupSql | Set-Content -Encoding utf8NoBOM -LiteralPath $backupPath
```

Armazenar backups fora do Git, com acesso restrito e criptografia no armazenamento externo.
Proposta operacional: copia diaria apos o expediente, manter sete copias diarias e quatro semanais,
com retencao final aprovada pelo responsavel do laboratorio/LGPD. Agendamento e armazenamento
externo nao estao automatizados neste projeto. RPO proposto: ate 24h; RTO nao medido em producao.

## Verificar restauracao sem sobrescrever dados

O script aceita somente banco **novo** com prefixo `<MYSQL_DATABASE>_restore_test_`, recusa destino
existente e exige backup confiavel gerado pelo script acima. Requer acesso administrativo local
ao MySQL, sem senha no comando. Nunca receber dumps de terceiros como entrada confiavel.

```powershell
docker compose cp database/operations/restore-test.sh mysql:/tmp/lab-restore-test.sh
# Use o nome do banco configurado no .env no lugar de atendimento, se diferente.
$restoreName = "atendimento_restore_test_" + (Get-Date -Format yyyyMMddHHmmss)
Get-Content -Raw -LiteralPath $backupPath | docker compose exec -T -e "RESTORE_DATABASE=$restoreName" mysql sh /tmp/lab-restore-test.sh
if ($LASTEXITCODE -ne 0) { throw "Restauracao falhou; conferir destino parcial sem tocar na origem." }
```

Conferir contagens, chaves, hash dos dados de teste, migrations e fluxo da aplicacao numa instancia
isolada apontando para o banco restaurado. O script nunca troca DATABASE_URL nem promove o banco
restaurado a producao. Se houver falha parcial, o destino e preservado para diagnostico; usar outro
nome em nova tentativa. Promocao em producao exige plano do responsavel, backup e janela de manutencao.

Na apresentacao, demonstrar falha usando somente containers de revisao: parar backend/banco,
observar erro/reconexao, reiniciar e conferir snapshot e consistencia. Nao executar essa demonstracao
contra um ambiente utilizado por clientes reais.

## Plano de apresentação sem internet

Antes da apresentação, com conexão e na máquina preparada, construir as imagens e guardar
a especificação OpenAPI local. Os arquivos abaixo ficam em `backups/`, ignorado pelo Git.

```powershell
docker compose build
docker compose pull mysql
New-Item -ItemType Directory -Force backups | Out-Null
$demoImages = docker compose config --images | Sort-Object -Unique
docker image save --output backups/imagens-demo.tar $demoImages
Invoke-WebRequest http://localhost:5000/api/v1/docs/openapi.json -OutFile backups/openapi.json
```

Na máquina offline, carregar as imagens se necessário (`docker image load --input backups/imagens-demo.tar`)
e executar `docker compose up -d --no-build --pull never`. Levar o `.env` privado e o banco/backup de
demonstração separadamente: imagens não contêm os volumes MySQL. Ensaiar a inicialização antes
da aula. O frontend estático é local; o Swagger UI usa CDN, então sem internet consultar o JSON
OpenAPI salvo ou `/api/v1/docs/openapi.json`. Não afirmar que o Swagger UI é inteiramente offline.
