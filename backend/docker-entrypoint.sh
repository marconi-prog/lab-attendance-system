#!/bin/sh
set -e
# Aplica as migrations e garante os guichês iniciais antes de subir a API.
flask db upgrade
flask seed --counters "${SEED_COUNTERS:-5}"
exec "$@"
