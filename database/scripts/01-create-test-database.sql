-- Executado automaticamente pelo container MySQL na primeira inicialização
-- (montado em /docker-entrypoint-initdb.d). Cria o banco usado pelos testes
-- automatizados e concede acesso ao usuário da aplicação.
CREATE DATABASE IF NOT EXISTS atendimento_test
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

GRANT ALL PRIVILEGES ON atendimento_test.* TO 'atendimento'@'%';
FLUSH PRIVILEGES;
