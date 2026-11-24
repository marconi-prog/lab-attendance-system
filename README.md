# Sistema de Controle de Atendimento — Laboratório de Análises Clínicas

Repositório `lab-attendance-system`. Sistema full stack de senhas: **totem** de emissão, **painel** público
com áudio em tempo real, **tela do atendente** e **área do gestor** (indicadores, relatórios, usuários,
guichês e auditoria).

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12, Flask 3, SQLAlchemy 2, Alembic, Flask-JWT-Extended, Flask-SocketIO, Pydantic 2, Gunicorn |
| Banco | MySQL 8.0 (InnoDB) |
| Frontend | Expo SDK 58, React Native + React Native Web, TypeScript, Expo Router, TanStack Query, Axios, Socket.IO Client, React Hook Form + Zod, Expo Speech, Lucide |
| Infra | Docker, Docker Compose, health checks, variáveis de ambiente |

Para desenvolvimento do frontend, use Node.js 22 ou 24 e npm. O Docker usa Node 22;
as verificações também passaram em Node 24. React 19.3.0, React Native 0.88.1 e TypeScript 6.0.3
estão declarados em [`frontend/package.json`](frontend/package.json); as demais versões exatas estão
no [`package-lock.json`](frontend/package-lock.json) e em [`backend/requirements.txt`](backend/requirements.txt).

Documentação: [`docs/architecture.md`](docs/architecture.md) · [`docs/database.md`](docs/database.md) ·
[`docs/api.md`](docs/api.md) · [`docs/requirements.md`](docs/requirements.md) ·
[`docs/conformidade.md`](docs/conformidade.md) (matriz requisito/evidência/situação) ·
[`docs/entrega.md`](docs/entrega.md) (checklist de entrega e pendências) · Swagger em `http://localhost:5000/api/docs`.

Os comandos abaixo usam **PowerShell (Windows)**. Equivalentes para bash (Linux/macOS) aparecem nos
blocos recolhíveis.

---

## 1. Funcionalidades

| Perfil | Funcionalidades |
|---|---|
| Cliente (sem login) | Totem: emissão de senha **SP** (prioritária), **SE** (retirada de exames) ou **SG** (geral), código `YYMMDD-PPSQ`, sequência diária por categoria |
| Painel (público) | Senha chamada, 5 últimas chamadas, próximas por fila, atualização em tempo real (Socket.IO), sinal sonoro e voz `pt-BR` |
| Atendente (`ATTENDANT`) | Escolher guichê autorizado; chamar próxima (ciclo SP → SE/SG → SP); repetir chamada; iniciar e finalizar atendimento; registrar ausência após a 2ª chamada |
| Gestor (`ADMIN`) | Indicadores do dia; relatórios diário, mensal e por período; usuários e guichês autorizados; guichês; auditoria; encerramento do expediente |
| Sistema | Expediente (America/Recife): emissão 06:00–17:00, chamadas 07:00–17:00, encerramento automático às 17:00; JWT com refresh e revogação; OpenAPI/Swagger |

## 2. Execução rápida com Docker (recomendado)

Pré-requisitos: Docker 24+ com Docker Compose e Python (só para gerar os segredos).

```powershell
Copy-Item .env.example .env
# Edite .env: defina as senhas do MySQL e gere os segredos (um para JWT_SECRET_KEY, outro para SECRET_KEY):
python -c "import secrets; print(secrets.token_urlsafe(64))"

docker compose up -d --build
docker compose ps            # aguarde mysql, backend e frontend ficarem "healthy"
```

<details><summary>bash</summary>

```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
docker compose up -d --build
docker compose ps
```
</details>

O backend aplica as migrations e cria os guichês 01–05 automaticamente ao subir.

**Criar o primeiro administrador** (a senha é pedida no terminal, nunca fica no código):

```powershell
docker compose exec backend flask create-admin --name "Administrador" --email admin@laboratorio.com.br
```

Acesse:

| Endereço | Uso |
|---|---|
| http://localhost:8080 | Início (escolha Totem, Painel ou Equipe) |
| http://localhost:8080/totem | Totem de emissão |
| http://localhost:8080/panel | Painel da TV (clique uma vez para liberar o áudio) |
| http://localhost:8080/login | Login de atendentes e gestores |
| http://localhost:5000/api/docs | Swagger / OpenAPI |
| http://localhost:5000/api/health | Health check |

Fluxo de demonstração no Docker: entre como gestor → **Usuários** → crie um atendente marcando os
guichês autorizados → em outra aba entre como atendente, escolha o guichê → emita senhas no totem →
**Chamar próxima** e acompanhe o painel.

> O Compose sobe o backend com `FLASK_ENV=production`; por isso o comando de demonstração
> `flask seed-demo` (§3.4) é **recusado** no Docker. Use `create-admin` + cadastro pela interface.

> Fora do horário (emissão 06h–17h, chamadas 07h–17h, America/Recife) as operações são bloqueadas.
> Para demonstrar fora do expediente, use `ENFORCE_BUSINESS_HOURS=false` no `.env` e rode
> `docker compose up -d` novamente. Não use essa opção em produção.

## 3. Execução local (desenvolvimento)

### 3.1 MySQL

Use o MySQL do compose (`docker compose up -d mysql`) ou um MySQL 8 próprio:

```sql
CREATE DATABASE atendimento      CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE DATABASE atendimento_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'atendimento'@'%' IDENTIFIED BY 'sua-senha';
GRANT ALL PRIVILEGES ON atendimento.*      TO 'atendimento'@'%';
GRANT ALL PRIVILEGES ON atendimento_test.* TO 'atendimento'@'%';
```

(O container já cria `atendimento_test` via `database/scripts/01-create-test-database.sql`.)

### 3.2 Backend

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1   # se a ativação for bloqueada, veja a nota abaixo
pip install -r requirements-dev.txt
Copy-Item .env.example .env    # preencha DATABASE_URL, TEST_DATABASE_URL, SECRET_KEY, JWT_SECRET_KEY

flask db upgrade               # migrations (Alembic)
flask seed                     # guichês 01–05 (idempotente)
flask create-admin --name "Administrador" --email admin@laboratorio.com.br
python run.py                  # http://localhost:5000  (API + Socket.IO)
```

<details><summary>bash</summary>

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
flask db upgrade && flask seed
flask create-admin --name "Administrador" --email admin@laboratorio.com.br
python run.py
```
</details>

> **Ativação bloqueada pela política de execução?** Não é preciso alterar a política: chame o Python do
> ambiente diretamente, ex.: `.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt`,
> `.\.venv\Scripts\python.exe -m flask db upgrade`, `.\.venv\Scripts\python.exe -m pytest tests_isolated`
> e `.\.venv\Scripts\python.exe run.py`.

Comandos úteis: `flask db migrate -m "descrição"` (nova migration), `flask close-day` (encerra o expediente manualmente).

### 3.3 Frontend

```powershell
cd frontend
npm ci                         # instala exatamente as versões do package-lock.json
Copy-Item .env.example .env    # EXPO_PUBLIC_API_URL=http://localhost:5000
npm run web                    # navegador (http://localhost:8081)
npm start                      # Expo Go / emulador (use o IP da máquina em EXPO_PUBLIC_API_URL)
npm run typecheck              # verificação TypeScript
npm run lint                   # ESLint (configuração versionada)
npm run build:web              # build estático em dist/
```

### 3.4 Dados de demonstração (`flask seed-demo`)

Comando **somente para demonstração**, em ambiente local de desenvolvimento (`FLASK_ENV=development`
no `backend/.env`). Cria um **gestor** (perfil `ADMIN`) e um **atendente** (perfil `ATTENDANT`) com
permissão no guichê 01 (criando o guichê se ele não existir).

```powershell
flask seed-demo --dry-run          # mostra o que seria criado; não grava e não pede senhas
flask seed-demo --confirm-demo     # executa; as senhas são digitadas no terminal (não aparecem)
```

Opções: `--manager-email`, `--manager-name`, `--attendant-email`, `--attendant-name` e `--counter N`
(repita para vários guichês). Padrões: `gestor.demo@laboratorio.local` e `atendente.demo@laboratorio.local`.

Alternativa às senhas digitadas: variáveis `DEMO_MANAGER_PASSWORD` e `DEMO_ATTENDANT_PASSWORD`, definidas
só na sessão do terminal (sem ficar no histórico) e removidas em seguida:

```powershell
$env:DEMO_MANAGER_PASSWORD = [System.Net.NetworkCredential]::new('', (Read-Host 'Senha do gestor' -AsSecureString)).Password
$env:DEMO_ATTENDANT_PASSWORD = [System.Net.NetworkCredential]::new('', (Read-Host 'Senha do atendente' -AsSecureString)).Password
flask seed-demo --confirm-demo
Remove-Item Env:DEMO_MANAGER_PASSWORD, Env:DEMO_ATTENDANT_PASSWORD
```

Garantias:

* **Opt-in explícito** (`--confirm-demo`) e **recusado** com `FLASK_ENV=production` ou qualquer valor
  diferente de `development` — antes de acessar o banco.
* **Idempotente**: rodar de novo não cria nada; contas e guichês existentes e compatíveis são reaproveitados.
* **Não apaga, não sobrescreve e não redefine senhas.** Conta existente com perfil diferente, inativa
  ou sem permissão no guichê pedido — ou guichê inativo — **aborta** a execução sem gravar nada.
* **Senhas validadas**: mínimo de 8 caracteres com letras e números (regra da API), máximo de 128, sem
  espaços nas pontas, sem conter o identificador do e-mail e diferentes entre gestor e atendente.
* **Transação atômica**: guichês, contas, permissões e auditoria (`DEMO_SEED_*`) são gravados juntos ou nada é gravado.
* **Não emite senhas de atendimento**: ao final o comando imprime o roteiro — emitir pelo totem
  (06:00–17:00) e chamar pelo atendente (07:00–17:00), conforme os horários configurados.

## 4. Testes

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest tests_isolated          # seguro: SQLite temporário, não usa MySQL (comando seed-demo)
pytest                         # suíte completa — APAGA E RECRIA o banco de TEST_DATABASE_URL
pytest --cov=app               # com cobertura (mesmo aviso acima)
```

> **Atenção.** Os testes em `tests/` rodam contra **MySQL real** (banco `TEST_DATABASE_URL`), pois as
> garantias de concorrência dependem do InnoDB. A fixture automática de `tests/conftest.py` **apaga e
> recria** esse banco — isso vale também para `pytest tests/unit`. Nunca aponte `TEST_DATABASE_URL` para
> um banco com dados (o conftest exige `test` no nome do banco, mas não verifica o servidor).

Cenários cobertos pela suíte: emissão e sequência diária, duplicidade com 40 emissões simultâneas, ciclo
de prioridade, máquina de estados (todas as 64 combinações), 10 atendentes chamando ao mesmo tempo,
início/fim de atendimento, ausência após duas chamadas, expediente, autenticação, autorização por perfil,
relatórios, painel e Socket.IO.

Última validação registrada (23/11/2026): **196 testes** de `tests/` aprovados em MySQL 8.0 descartável e
**39 testes** de `tests_isolated/` aprovados em SQLite temporário; `flask db upgrade` e `flask seed-demo`
validados em bancos descartáveis. Instalação limpa (`npm ci`), TypeScript, lint e build web passaram.
O Docker Compose foi construído e executado em projeto/volume de revisão separados: os três serviços
ficaram saudáveis e o fluxo de atendimento passou via API. A nova execução completa aprovou **235 testes**.
O fluxo guiado das telas foi verificado e o solicitante confirmou sinal e voz. Veja o
[`registro da interface`](docs/validacao-interface.md). A conferência dos enunciados originais continua
pendente — detalhes em [`docs/conformidade.md`](docs/conformidade.md).

## 5. Estrutura

```text
backend/    app/{config,extensions,models,repositories,services,controllers,routes,schemas,middlewares,sockets,utils,docs}
            app/cli.py  app/demo_seed.py  migrations/  tests/{unit,integration}  tests_isolated/  run.py  wsgi.py  Dockerfile
frontend/   app/{(auth),(attendant),(manager),totem,panel}  src/{components,services,hooks,contexts,types,utils,constants,theme}
database/   scripts/ (init do MySQL)  seeds/  README.md
docs/       architecture.md  database.md  api.md  requirements.md  conformidade.md  entrega.md
```

## 6. Segurança (resumo)

Senhas com hash scrypt · JWT de acesso (30 min) + refresh (7 dias) com revogação no logout ·
perfil verificado no banco a cada requisição (desativar usuário corta o acesso na hora) · validação
Pydantic com rejeição de campos desconhecidos · erros padronizados · CORS e Socket.IO restritos a
`CORS_ORIGINS` · namespace `/staff` exige JWT · logs sem corpo de requisição, tokens ou senhas ·
nenhuma credencial no código (a aplicação não sobe sem os segredos no ambiente) · nunca versione `.env`.

## 7. Fluxo de trabalho: `dev` → validação → PR → `main`

1. **Desenvolvimento na `dev`** (ou em branches curtas criadas a partir da `dev` e integradas nela).
2. **Validação na `dev`**: `pytest tests_isolated`, suíte completa contra banco de testes dedicado,
   `npm run typecheck`, `docker compose up` em máquina limpa e roteiro de demonstração
   (checklist em [`docs/entrega.md`](docs/entrega.md) §5).
3. **Pull request `dev` → `main`** no GitHub, com o resultado das validações e revisão de pelo menos um
   integrante que não seja o autor.
4. **Merge em `main`** somente após aprovação — `main` é sempre a versão entregável. Sem push direto na `main`.
5. **Tag** da versão entregue na `main` (nome a definir — pendente).

## 8. Limitações conhecidas

* A suíte de testes depende de MySQL real e apaga o banco de testes; apenas `tests_isolated/` roda sem MySQL.
* Não há suíte E2E automatizada de interface no frontend (há TypeScript, lint e validação guiada registrada).
  Repita o áudio no equipamento da apresentação para conferir saída de som, volume e voz.
* Builds nativos (Android/iOS) não foram validados; o uso principal é web (Docker/nginx) e Expo Go.
* `flask seed-demo` só funciona em desenvolvimento; no Docker (produção) é recusado por projeto.
* O áudio do painel exige um clique para ser liberado pelo navegador; sem síntese de voz, toca só o sinal sonoro.
* Socket.IO em 1 worker (escalar exige Redis como `message_queue`); sem rate limit no totem; na web os
  tokens ficam em `sessionStorage` (ver riscos em [`docs/architecture.md`](docs/architecture.md)).
* Pela leitura literal da regra, SE tem preferência sobre SG após SP, o que pode atrasar SG.
* Os enunciados originais não estão no repositório; a conformidade foi derivada da documentação existente.

## 9. Declaração de uso de inteligência artificial

* **Preparação acadêmica iniciada em 23/11/2026:** o **Codex** (OpenAI) coordena as tarefas e o
  **Claude Code** (Anthropic) auxilia na execução. Neste lote, o Claude Code redigiu
  `docs/conformidade.md`, `docs/entrega.md` e esta revisão do README, e implementou o comando
  `flask seed-demo` com seus testes isolados, a configuração de lint e os ajustes de Hooks do frontend.
  O Codex revisou os diffs, executou as validações registradas e organizou os commits. A equipe deve
  revisar o resultado e saber explicar o código na apresentação.
* **Histórico anterior** (incluindo os commits de 10/11/2026): o uso de IA é **desconhecido** — não há
  registro no repositório. A equipe deve completar esta declaração.

## 10. Equipe

Identificação operacional: **Equipe lab-attendance-system** (não é o nome oficial da equipe, ainda não
informado).

| Nome | Matrícula |
|---|---|
| Karllyson Paula | 01861379 |
| Marconi Farias Araújo | 01783919 |
| Gustavo Buled Martins | 01797483 |
| Sérgio Luiz dos Santos Neto | 01819969 |
| Pedro Henrique Rodrigues da Silva | 01794091 |
| Janildo Caluête de Farias Júnior | 01799458 |

Usuários GitHub e colaboradores: ver [`docs/entrega.md`](docs/entrega.md).

## 11. Licença

Distribuído sob a licença **MIT** — ver [`LICENSE`](LICENSE).
