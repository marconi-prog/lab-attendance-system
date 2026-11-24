"""Fixtures dos testes ISOLADOS (sem MySQL).

Esta pasta fica fora de ``tests/`` de propósito: o ``tests/conftest.py``
possui fixtures automáticas que recriam e limpam o banco ``TEST_DATABASE_URL``.
Aqui nada disso é carregado — cada teste usa um app Flask mínimo com um
arquivo SQLite temporário (``tmp_path``), descartado ao final.

Rodar: ``cd backend; pytest tests_isolated``
"""
from __future__ import annotations

import pytest
from flask import Flask
from sqlalchemy import func, select

from app.demo_seed import ATTENDANT_PASSWORD_ENV, MANAGER_PASSWORD_ENV, seed_demo_command
from app.extensions import db
from app.models import Counter, User


@pytest.fixture()
def demo_app(tmp_path, monkeypatch):
    # Ambiente controlado: nada herdado de um .env local influencia o teste.
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv(MANAGER_PASSWORD_ENV, raising=False)
    monkeypatch.delenv(ATTENDANT_PASSWORD_ENV, raising=False)

    app = Flask("seed_demo_isolated")
    app.config.update(
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{(tmp_path / 'seed_demo.sqlite').as_posix()}",
        ENV_NAME="development",
        TESTING=True,
    )
    assert app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:///"), "teste isolado deve usar SQLite"
    db.init_app(app)
    app.cli.add_command(seed_demo_command)
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture()
def run_seed(demo_app):
    def _run(*args: str):
        return demo_app.test_cli_runner().invoke(args=["seed-demo", *args])

    return _run


@pytest.fixture()
def db_snapshot(demo_app):
    """Retrato completo do banco: contagem por tabela, usuários (com hash) e guichês."""

    def _snapshot() -> dict:
        with demo_app.app_context():
            tables = {
                table.name: db.session.execute(select(func.count()).select_from(table)).scalar_one()
                for table in db.metadata.sorted_tables
            }
            users = {
                user.email: (
                    user.name, user.role, user.active, user.password_hash,
                    tuple(sorted(c.number for c in user.counters)), user.updated_at,
                )
                for user in db.session.scalars(select(User))
            }
            counters = {c.number: (c.name, c.active, c.updated_at) for c in db.session.scalars(select(Counter))}
            db.session.remove()
            return {"tables": tables, "users": users, "counters": counters}

    return _snapshot
