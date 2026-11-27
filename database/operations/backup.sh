#!/bin/sh
# Executar no conteiner MySQL; SQL vai para stdout e credenciais ficam no ambiente.
set -eu
: "${MYSQL_DATABASE:?Defina MYSQL_DATABASE}"
: "${MYSQL_USER:?Defina MYSQL_USER}"
: "${MYSQL_PASSWORD:?Defina MYSQL_PASSWORD}"
case "$MYSQL_DATABASE" in *[!a-zA-Z0-9_]*|'') echo 'Nome de banco invalido.' >&2; exit 2;; esac
export MYSQL_PWD="$MYSQL_PASSWORD"
exec mysqldump --user="$MYSQL_USER" --single-transaction --quick --routines --triggers \
  --no-tablespaces --set-gtid-purged=OFF --default-character-set=utf8mb4 "$MYSQL_DATABASE"
