#!/bin/sh
# Restaura somente em um banco de verificacao NOVO. Nunca substitui o banco de origem.
set -eu
: "${MYSQL_DATABASE:?Defina MYSQL_DATABASE de origem}"
: "${MYSQL_ROOT_PASSWORD:?Requer administrador para criar o banco de verificacao}"
: "${RESTORE_DATABASE:?Defina RESTORE_DATABASE}"
for db_name in "$MYSQL_DATABASE" "$RESTORE_DATABASE"; do
  case "$db_name" in *[!a-zA-Z0-9_]*|'') echo 'Nome de banco invalido.' >&2; exit 2;; esac
done
case "$RESTORE_DATABASE" in "$MYSQL_DATABASE"_restore_test_?*) ;; *) echo 'Destino deve ter prefixo <origem>_restore_test_.' >&2; exit 2;; esac
export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"
exists=$(mysql --user=root --batch --skip-column-names -e "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='$RESTORE_DATABASE'")
if [ -n "$exists" ]; then echo 'Destino ja existe; nenhuma alteracao realizada.' >&2; exit 2; fi
dump_file=$(mktemp)
trap 'rm -f "$dump_file"' EXIT HUP INT TERM
cat > "$dump_file"
if [ ! -s "$dump_file" ]; then echo 'Backup vazio; nenhuma alteracao realizada.' >&2; exit 2; fi
if grep -Eiq '^[[:space:]]*(USE[[:space:]]|CREATE[[:space:]]+DATABASE|DROP[[:space:]]+DATABASE)' "$dump_file"; then
  echo 'Backup contem selecao/criacao/exclusao de banco; use o backup.sh deste projeto.' >&2; exit 2
fi
mysql --user=root -e "CREATE DATABASE \`$RESTORE_DATABASE\` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
mysql --user=root --database="$RESTORE_DATABASE" < "$dump_file"
tables=$(mysql --user=root --batch --skip-column-names -e "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='$RESTORE_DATABASE'")
echo "Restauracao de verificacao concluida em $RESTORE_DATABASE ($tables tabelas). Origem preservada."
