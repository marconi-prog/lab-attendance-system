# Sistema de Controle de Atendimento — Laboratório de Análises Clínicas

Sistema full stack de senhas: **totem** de emissão, **painel** público com áudio em tempo real,
**tela do atendente** e **área do gestor** (indicadores, relatórios, usuários, guichês e auditoria).

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12, Flask 3, SQLAlchemy 2, Alembic, Flask-JWT-Extended, Flask-SocketIO, Pydantic 2, Gunicorn |
| Banco | MySQL 8.0 (InnoDB) |
| Frontend | Expo SDK 58, React Native + React Native Web, TypeScript, Expo Router, TanStack Query, Axios, Socket.IO Client, React Hook Form + Zod, Expo Speech, Lucide |
| Infra | Docker, Docker Compose, health checks, variáveis de ambiente |

Documentação detalhada: [`docs/architecture.md`](docs/architecture.md) · [`docs/database.md`](docs/database.md) ·
[`docs/api.md`](docs/api.md) · [`docs/requirements.md`](docs/requirements.md) · Swagger em `http://localhost:5000/api/docs`.

---

## 1. Execução rápida com Docker (recomendado)

Pré-requisitos: Docker 24+ com Docker Compose.

```bash
cp .env.example .env
# Edite .env: defina senhas do MySQL e gere os segredos:
python3 -c "import secrets; print(secrets.token_urlsafe(64))"   # use em JWT_SECRET_KEY e SECRET_KEY

docker compose up -d --build
docker compose ps            # aguarde mysql, backend e frontend ficarem "healthy"
```

O backend aplica as migrations e cria os guichês 01–05 automaticamente ao subir.

**Criar o primeiro administrador** (a senha é pedida no terminal, nunca fica no código):

```bash
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

Fluxo de demonstração: entre como gestor → **Usuários** → crie um atendente marcando os guichês
autorizados → em outra aba entre como atendente, escolha o guichê → emita senhas no totem →
**Chamar próxima** e acompanhe o painel.

> Fora do horário 07h–17h (America/Recife) as chamadas são bloqueadas. Para demonstrar fora do
> expediente, use `ENFORCE_BUSINESS_HOURS=false` no `.env` e rode `docker compose up -d` novamente.

## 2. Execução local (desenvolvimento)

### 2.1 MySQL

Use o MySQL do compose (`docker compose up -d mysql`) ou um MySQL 8 próprio:

```sql
CREATE DATABASE atendimento      CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE DATABASE atendimento_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'atendimento'@'%' IDENTIFIED BY 'sua-senha';
GRANT ALL PRIVILEGES ON atendimento.*      TO 'atendimento'@'%';
GRANT ALL PRIVILEGES ON atendimento_test.* TO 'atendimento'@'%';
```

(O container já cria `atendimento_test` via `database/scripts/01-create-test-database.sql`.)

### 2.2 Backend

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # preencha DATABASE_URL, TEST_DATABASE_URL, SECRET_KEY, JWT_SECRET_KEY

flask db upgrade              # migrations (Alembic)
flask seed                    # guichês 01–05 (idempotente)
flask create-admin --name "Administrador" --email admin@laboratorio.com.br
python run.py                 # http://localhost:5000  (API + Socket.IO)
```

Comandos úteis: `flask db migrate -m "descrição"` (nova migration), `flask close-day` (encerra o expediente manualmente).

### 2.3 Frontend

```bash
cd frontend
npm install
cp .env.example .env          # EXPO_PUBLIC_API_URL=http://localhost:5000
npm run web                   # navegador (http://localhost:8081)
npm start                     # Expo Go / emulador (use o IP da máquina em EXPO_PUBLIC_API_URL)
npm run typecheck             # verificação TypeScript
npm run build:web             # build estático em dist/
```

## 3. Testes

Os testes rodam contra **MySQL real** (banco `atendimento_test`, definido em `TEST_DATABASE_URL`), pois
as garantias de concorrência dependem do InnoDB. O banco de testes é recriado e limpo a cada execução.

```bash
cd backend && source .venv/bin/activate
pytest                         # todos
pytest tests/unit              # regras puras (sem banco)
pytest --cov=app               # com cobertura
```

Cobertura: emissão e sequência diária, duplicidade com 40 emissões simultâneas, ciclo de prioridade,
máquina de estados (todas as 64 combinações), 10 atendentes chamando ao mesmo tempo, início/fim de
atendimento, ausência após duas chamadas, expediente, autenticação, autorização por perfil, relatórios,
painel e Socket.IO.

## 4. Estrutura

```text
backend/    app/{config,extensions,models,repositories,services,controllers,routes,schemas,middlewares,sockets,utils,docs}
            migrations/  tests/{unit,integration}  run.py  wsgi.py  Dockerfile
frontend/   app/{(auth),(attendant),(manager),totem,panel}  src/{components,services,hooks,contexts,types,utils,constants,theme}
database/   scripts/ (init do MySQL)  seeds/  README.md
docs/       architecture.md  database.md  api.md  requirements.md
```

## 5. Segurança (resumo)

Senhas com hash scrypt · JWT de acesso (30 min) + refresh (7 dias) com revogação no logout ·
perfil verificado no banco a cada requisição (desativar usuário corta o acesso na hora) · validação
Pydantic com rejeição de campos desconhecidos · erros padronizados · CORS e Socket.IO restritos a
`CORS_ORIGINS` · namespace `/staff` exige JWT · logs sem corpo de requisição, tokens ou senhas ·
nenhuma credencial no código (a aplicação não sobe sem os segredos no ambiente).
# lab-attendance-system
