"""Migração 0002 (gestor ativo único) sobre dados existentes — SQLite temporário."""
from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from flask import Flask
from flask_migrate import Migrate
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.extensions import db

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"
BASE, HEAD = "0001_schema_inicial", "0002_gestor_ativo_unico"
NOW = "2026-11-10 12:00:00"


@pytest.fixture()
def mig_app(tmp_path):
    app = Flask("migration_isolated")
    app.config.update(SQLALCHEMY_DATABASE_URI=f"sqlite:///{(tmp_path / 'migration.sqlite').as_posix()}", TESTING=True)
    assert app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:///"), "teste isolado deve usar SQLite"
    db.init_app(app)
    Migrate(app, db, directory=str(MIGRATIONS))
    with app.app_context():
        yield app
        db.session.remove()
        db.engine.dispose()


def alembic(revision: str, *, down: bool = False) -> None:
    cfg = Config(str(MIGRATIONS / "alembic.ini"))
    cfg.set_main_option("script_location", str(MIGRATIONS))
    (command.downgrade if down else command.upgrade)(cfg, revision)


def execute(sql: str, **params):
    with db.engine.begin() as conn:
        return conn.execute(text(sql), params)


def add_user(user_id: int, role: str, active: bool) -> None:
    execute(
        "INSERT INTO users (id, name, email, password_hash, role, active, created_at, updated_at) "
        "VALUES (:id, :name, :email, :hash, :role, :active, :now, :now)",
        id=user_id, name=f"Usuário {user_id}", email=f"u{user_id}@lab.test", hash=f"hash-{user_id}",
        role=role, active=active, now=NOW,
    )


def seed_existing_data() -> None:
    """Dados de uma instalação em produção antes da migração 0002."""
    add_user(1, "ADMIN", True)
    add_user(2, "ADMIN", False)
    add_user(3, "ATTENDANT", True)
    add_user(4, "ATTENDANT", False)
    execute("INSERT INTO counters (id, name, number, active, created_at, updated_at) VALUES (1, 'Guichê 01', 1, 1, :n, :n)", n=NOW)
    execute("INSERT INTO user_counters (user_id, counter_id) VALUES (1, 1), (3, 1)")
    execute("INSERT INTO counter_sessions (id, counter_id, user_id, opened_at) VALUES (1, 1, 3, :n)", n=NOW)
    execute("INSERT INTO audit_logs (id, user_id, action, entity, created_at) VALUES (1, 1, 'LOGIN', 'user', :n)", n=NOW)


def snapshot() -> dict:
    return {
        table: execute(f"SELECT {cols} FROM {table} ORDER BY 1").all()
        for table, cols in {
            "users": "id, name, email, password_hash, role, active, created_at, updated_at",
            "counters": "id, name, number, active",
            "user_counters": "user_id, counter_id",
            "counter_sessions": "id, counter_id, user_id, opened_at, closed_at",
            "audit_logs": "id, user_id, action",
        }.items()
    }


def version() -> str:
    return execute("SELECT version_num FROM alembic_version").scalar_one()


def user_columns() -> set[str]:
    return {c["name"] for c in inspect(db.engine).get_columns("users")}


def test_upgrade_preserves_existing_data_and_enforces_single_manager(mig_app):
    alembic(BASE)
    seed_existing_data()
    before = snapshot()

    alembic("head")

    assert version() == HEAD
    assert snapshot() == before  # nenhum dado alterado
    assert execute("SELECT id, active_manager_slot FROM users ORDER BY id").all() == [(1, 1), (2, None), (3, None), (4, None)]
    indexes = {ix["name"]: ix for ix in inspect(db.engine).get_indexes("users")}
    assert indexes["uq_users_active_manager_slot"]["unique"]
    with pytest.raises(IntegrityError):
        execute("UPDATE users SET active = 1 WHERE id = 2")  # reativação direta bloqueada
    with pytest.raises(IntegrityError):
        add_user(5, "ADMIN", True)
    assert snapshot() == before


def test_upgrade_aborts_before_ddl_when_multiple_active_managers_exist(mig_app):
    alembic(BASE)
    seed_existing_data()
    add_user(6, "ADMIN", True)
    add_user(7, "ADMIN", True)
    before = snapshot()

    with pytest.raises(RuntimeError) as exc:
        alembic("head")

    message = str(exc.value)
    assert "3 gestores" in message and "1, 6, 7" in message and "Nenhum dado foi alterado" in message
    assert version() == BASE
    assert "active_manager_slot" not in user_columns()  # nenhuma DDL executada
    assert snapshot() == before  # ninguém foi desativado nem rebaixado


def test_downgrade_removes_only_the_constraint(mig_app):
    alembic(BASE)
    seed_existing_data()
    before = snapshot()
    alembic("head")

    alembic(BASE, down=True)

    assert version() == BASE
    assert "active_manager_slot" not in user_columns()
    assert snapshot() == before
