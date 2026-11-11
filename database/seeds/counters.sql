-- Guichês iniciais (equivalente a `flask seed`). Idempotente.
-- Uso: mysql -u atendimento -p atendimento < database/seeds/counters.sql
INSERT IGNORE INTO counters (name, number, active, created_at, updated_at) VALUES
  ('Guichê 01', 1, 1, UTC_TIMESTAMP(), UTC_TIMESTAMP()),
  ('Guichê 02', 2, 1, UTC_TIMESTAMP(), UTC_TIMESTAMP()),
  ('Guichê 03', 3, 1, UTC_TIMESTAMP(), UTC_TIMESTAMP()),
  ('Guichê 04', 4, 1, UTC_TIMESTAMP(), UTC_TIMESTAMP()),
  ('Guichê 05', 5, 1, UTC_TIMESTAMP(), UTC_TIMESTAMP());
