"""Migração 0002 (gestor ativo único) no MySQL de teste, sobre dados existentes.

O banco de teste é esvaziado, migrado pelo Alembic e, ao final, recriado com
``create_all`` para os demais testes.
"""
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.extensions import db as _db

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"
BASE, HEAD = "0001_schema_inicial", "0002_gestor_ativo_unico"
NOW = "2026-11-10 12:00:00"


def _drop_everything() -> None:
    _db.session.remove()
    _db.drop_all()
    with _db.engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))


@pytest.fixture()
def bare_db(app):
    with app.app_context():
        _drop_everything()
        yield
        _drop_everything()
        _db.create_all()


def alembic(revision: str, *, down: bool = False) -> None:
    cfg = Config(str(MIGRATIONS / "alembic.ini"))
    cfg.set_main_option("script_location", str(MIGRATIONS))
    (command.downgrade if down else command.upgrade)(cfg, revision)


def execute(sql: str, **params):
    with _db.engine.begin() as conn:
        return conn.execute(text(sql), params)


def add_user(user_id: int, role: str, active: bool) -> None:
    execute(
        "INSERT INTO users (id, name, email, password_hash, role, active, created_at, updated_at) "
        "VALUES (:id, :name, :email, :hash, :role, :active, :now, :now)",
        id=user_id, name=f"Usuário {user_id}", email=f"u{user_id}@lab.test", hash=f"hash-{user_id}",
        role=role, active=active, now=NOW,
    )


def seed_existing_data() -> None:
    add_user(1, "ADMIN", True)
    add_user(2, "ADMIN", False)
    add_user(3, "ATTENDANT", True)
    execute("INSERT INTO counters (id, name, number, active, created_at, updated_at) VALUES (1, 'Guichê 01', 1, 1, :n, :n)", n=NOW)
    execute("INSERT INTO user_counters (user_id, counter_id) VALUES (1, 1), (3, 1)")
    execute("INSERT INTO counter_sessions (id, counter_id, user_id, opened_at) VALUES (1, 1, 3, :n)", n=NOW)


def snapshot() -> dict:
    return {
        "users": execute("SELECT id, name, email, password_hash, role, active, created_at, updated_at FROM users ORDER BY id").all(),
        "user_counters": execute("SELECT user_id, counter_id FROM user_counters ORDER BY 1, 2").all(),
        "counter_sessions": execute("SELECT id, counter_id, user_id, opened_at, closed_at FROM counter_sessions").all(),
    }


def version() -> str:
    return execute("SELECT version_num FROM alembic_version").scalar_one()


def user_columns() -> set[str]:
    return {c["name"] for c in inspect(_db.engine).get_columns("users")}


def test_upgrade_preserves_data_and_enforces_single_manager(bare_db):
    alembic(BASE)
    seed_existing_data()
    before = snapshot()

    alembic("head")

    assert version() == HEAD
    assert snapshot() == before
    assert execute("SELECT id, active_manager_slot FROM users ORDER BY id").all() == [(1, 1), (2, None), (3, None)]
    with pytest.raises(IntegrityError):
        execute("UPDATE users SET active = 1 WHERE id = 2")
    with pytest.raises(IntegrityError):
        execute("UPDATE users SET role = 'ADMIN' WHERE id = 3")
    assert snapshot() == before


def test_upgrade_aborts_before_ddl_with_multiple_active_managers(bare_db):
    alembic(BASE)
    seed_existing_data()
    add_user(4, "ADMIN", True)
    before = snapshot()

    with pytest.raises(RuntimeError) as exc:
        alembic("head")

    assert "2 gestores" in str(exc.value) and "1, 4" in str(exc.value) and "Nenhum dado foi alterado" in str(exc.value)
    assert version() == BASE
    assert "active_manager_slot" not in user_columns()
    assert snapshot() == before


def test_downgrade_removes_only_the_constraint(bare_db):
    alembic(BASE)
    seed_existing_data()
    before = snapshot()
    alembic("head")
    alembic(BASE, down=True)
    assert version() == BASE
    assert "active_manager_slot" not in user_columns()
    assert snapshot() == before
