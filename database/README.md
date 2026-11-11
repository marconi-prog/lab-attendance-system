# Banco de dados

MySQL 8.0 (InnoDB, utf8mb4). O schema é gerenciado **somente** pelas migrations Alembic em
`backend/migrations` — não crie tabelas manualmente. Modelagem completa em [`docs/database.md`](../docs/database.md).

| Pasta | Conteúdo |
|---|---|
| `scripts/` | Executados pelo container MySQL na primeira inicialização (`/docker-entrypoint-initdb.d`). Cria o banco `atendimento_test`. |
| `seeds/` | Dados iniciais em SQL (guichês). O mesmo é feito por `flask seed`. Usuários **não** têm seed: o primeiro administrador é criado com `flask create-admin` (senha digitada, nunca versionada). |

## Operações

```bash
# aplicar migrations (local)
cd backend && flask db upgrade
# criar nova migration após alterar models
flask db migrate -m "descrição" && flask db upgrade
# no Docker
docker compose exec backend flask db upgrade
# backup
docker compose exec mysql sh -c 'mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" atendimento' > backup.sql
```

> O script de `scripts/` só roda quando o volume `mysql_data` é criado. Em um volume existente,
> crie o banco de testes manualmente com o SQL do arquivo.
