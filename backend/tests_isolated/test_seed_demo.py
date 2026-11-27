"""Testes do comando ``flask seed-demo`` (SQLite temporário — nunca toca o MySQL)."""
from __future__ import annotations

import getpass
from datetime import time

import pytest
from flask import Flask
from sqlalchemy import func, select

import app.demo_seed as demo_seed
from app.config.settings import DevelopmentConfig, ProductionConfig, TestingConfig
from app.demo_seed import (
    ATTENDANT_PASSWORD_ENV,
    DEFAULT_ATTENDANT_EMAIL,
    DEFAULT_MANAGER_EMAIL,
    MANAGER_PASSWORD_ENV,
)
from app.extensions import db
from app.models import AuditLog, Counter, Ticket, User, UserRole

# Valores fictícios, exclusivos destes testes.
MANAGER_PW = "Painel-Teste-41"
ATTENDANT_PW = "Guiche-Teste-73"
ORIGINAL_PW = "Original-Conta-9"
NO_CHANGES = "Nenhum dado foi alterado"


# ------------------------------------------------------------------ apoio
@pytest.fixture()
def passwords_env(monkeypatch):
    monkeypatch.setenv(MANAGER_PASSWORD_ENV, MANAGER_PW)
    monkeypatch.setenv(ATTENDANT_PASSWORD_ENV, ATTENDANT_PW)


@pytest.fixture()
def no_prompt(monkeypatch):
    def _fail(*_args, **_kwargs):
        raise AssertionError("seed-demo não deveria pedir senha neste cenário")

    monkeypatch.setattr(getpass, "getpass", _fail)


def add_counter(app: Flask, number: int, *, active: bool = True) -> None:
    with app.app_context():
        db.session.add(Counter(name=f"Guichê {number:02d}", number=number, active=active))
        db.session.commit()
        db.session.remove()


def add_user(app: Flask, *, email: str, role: UserRole, active: bool = True, counters: tuple[int, ...] = ()) -> None:
    with app.app_context():
        user = User(name="Conta pré-existente", email=email, role=role, active=active)
        user.set_password(ORIGINAL_PW)
        if counters:
            user.counters = list(db.session.scalars(select(Counter).where(Counter.number.in_(counters))))
        db.session.add(user)
        db.session.commit()
        db.session.remove()


def get_user(email: str) -> User:
    return db.session.scalars(select(User).where(func.lower(User.email) == email.lower())).one()


# ------------------------------------------------------------------ ambiente
@pytest.mark.parametrize(
    ("flask_env", "env_name"),
    [
        ("production", "production"),
        ("production", "development"),
        ("development", "production"),
        (None, "development"),
        ("staging", "development"),
        ("testing", "testing"),
    ],
)
def test_refused_outside_development_without_touching_db(
    demo_app, run_seed, db_snapshot, passwords_env, no_prompt, monkeypatch, flask_env, env_name
):
    if flask_env is None:
        monkeypatch.delenv("FLASK_ENV", raising=False)
    else:
        monkeypatch.setenv("FLASK_ENV", flask_env)
    demo_app.config["ENV_NAME"] = env_name
    before = db_snapshot()

    result = run_seed("--confirm-demo")

    assert result.exit_code != 0
    assert NO_CHANGES in result.output
    if "production" in (flask_env, env_name):
        assert "recusado em produção" in result.output
    assert db_snapshot() == before


def test_dry_run_is_also_refused_in_production(demo_app, run_seed, db_snapshot, monkeypatch, no_prompt):
    monkeypatch.setenv("FLASK_ENV", "production")
    before = db_snapshot()
    result = run_seed("--dry-run")
    assert result.exit_code != 0
    assert "recusado em produção" in result.output
    assert db_snapshot() == before


def test_requires_explicit_confirmation(run_seed, db_snapshot, passwords_env, no_prompt):
    before = db_snapshot()
    result = run_seed()
    assert result.exit_code != 0
    assert "--confirm-demo" in result.output
    assert db_snapshot() == before


def test_config_classes_expose_environment_name():
    assert DevelopmentConfig.ENV_NAME == "development"
    assert ProductionConfig.ENV_NAME == "production"
    assert TestingConfig.ENV_NAME == "testing"


def test_command_is_registered_with_existing_commands():
    from app.cli import register_cli

    bare = Flask("cli_registration_only")  # sem banco: apenas registra os comandos
    register_cli(bare)
    assert {"create-admin", "seed", "close-day", "seed-demo"} <= set(bare.cli.commands)


# ------------------------------------------------------------------ criação
def test_creates_manager_and_attendant_with_counter_permission(demo_app, run_seed, passwords_env, no_prompt):
    demo_app.config.update(
        TICKET_ISSUE_OPEN_TIME=time(7, 30), BUSINESS_OPEN_TIME=time(7, 0), BUSINESS_CLOSE_TIME=time(17, 0),
        TIMEZONE="America/Recife", ENFORCE_BUSINESS_HOURS=True,
    )
    result = run_seed("--confirm-demo")
    assert result.exit_code == 0, result.output

    with demo_app.app_context():
        manager = get_user(DEFAULT_MANAGER_EMAIL)
        attendant = get_user(DEFAULT_ATTENDANT_EMAIL)
        assert (manager.role, manager.active, manager.counters) == (UserRole.ADMIN, True, [])
        assert (attendant.role, attendant.active) == (UserRole.ATTENDANT, True)
        assert [c.number for c in attendant.counters] == [1]
        assert db.session.scalars(select(Counter).where(Counter.number == 1)).one().active is True
        assert manager.check_password(MANAGER_PW)
        assert attendant.check_password(ATTENDANT_PW)
        # nenhuma senha de atendimento (ticket) é emitida pelo comando
        assert db.session.scalar(select(func.count(Ticket.id))) == 0
        logs = list(db.session.scalars(select(AuditLog)))
        assert {log.action for log in logs} == {"DEMO_SEED_COUNTER_CREATED", "DEMO_SEED_USER_CREATED"}
        assert all(MANAGER_PW not in str(log.details) and ATTENDANT_PW not in str(log.details) for log in logs)

    assert MANAGER_PW not in result.output and ATTENDANT_PW not in result.output
    assert "Nenhuma senha de atendimento foi emitida" in result.output
    assert "/totem" in result.output and "07:30" in result.output and "17:00" in result.output


def test_multiple_counters_reuse_existing_and_create_missing(demo_app, run_seed, passwords_env, no_prompt):
    add_counter(demo_app, 2)
    add_counter(demo_app, 9)  # não solicitado: deve ficar intocado
    result = run_seed("--confirm-demo", "--counter", "2", "--counter", "3")
    assert result.exit_code == 0, result.output
    with demo_app.app_context():
        assert [c.number for c in get_user(DEFAULT_ATTENDANT_EMAIL).counters] == [2, 3]
        assert sorted(db.session.scalars(select(Counter.number))) == [2, 3, 9]
        assert db.session.scalar(select(func.count(Counter.id)).where(Counter.number == 9)) == 1


def test_password_prompt_path(demo_app, run_seed, monkeypatch):
    answers = iter([MANAGER_PW, MANAGER_PW, ATTENDANT_PW, ATTENDANT_PW])
    monkeypatch.setattr(getpass, "getpass", lambda *_a, **_k: next(answers))
    result = run_seed("--confirm-demo")
    assert result.exit_code == 0, result.output
    with demo_app.app_context():
        assert get_user(DEFAULT_MANAGER_EMAIL).check_password(MANAGER_PW)
        assert get_user(DEFAULT_ATTENDANT_EMAIL).check_password(ATTENDANT_PW)


def test_dry_run_writes_nothing_and_does_not_prompt(run_seed, db_snapshot, no_prompt):
    before = db_snapshot()
    result = run_seed("--dry-run")
    assert result.exit_code == 0, result.output
    assert "seria(m) criado(s)" in result.output
    assert db_snapshot() == before


# ------------------------------------------------------------------ idempotência e senhas
def test_second_run_is_idempotent_and_never_resets_passwords(demo_app, run_seed, db_snapshot, passwords_env, monkeypatch, no_prompt):
    assert run_seed("--confirm-demo").exit_code == 0
    before = db_snapshot()

    monkeypatch.setenv(MANAGER_PASSWORD_ENV, "Outra-Senha-11")
    monkeypatch.setenv(ATTENDANT_PASSWORD_ENV, "Outra-Senha-22")
    result = run_seed("--confirm-demo")

    assert result.exit_code == 0, result.output
    assert "NÃO foi alterada" in result.output
    assert "Tudo já estava preparado" in result.output
    assert db_snapshot() == before
    with demo_app.app_context():
        assert get_user(DEFAULT_MANAGER_EMAIL).check_password(MANAGER_PW)
        assert not get_user(DEFAULT_MANAGER_EMAIL).check_password("Outra-Senha-11")
        assert get_user(DEFAULT_ATTENDANT_EMAIL).check_password(ATTENDANT_PW)


def test_existing_compatible_accounts_are_reused_untouched(demo_app, run_seed, db_snapshot, no_prompt):
    add_counter(demo_app, 1)
    add_counter(demo_app, 2)
    add_user(demo_app, email=DEFAULT_MANAGER_EMAIL, role=UserRole.ADMIN)
    add_user(demo_app, email=DEFAULT_ATTENDANT_EMAIL, role=UserRole.ATTENDANT, counters=(1, 2))  # permissões extras são mantidas
    before = db_snapshot()

    result = run_seed("--confirm-demo")  # sem variáveis de senha: não pode pedir nada

    assert result.exit_code == 0, result.output
    assert db_snapshot() == before
    with demo_app.app_context():
        assert get_user(DEFAULT_MANAGER_EMAIL).check_password(ORIGINAL_PW)


# ------------------------------------------------------------------ incompatibilidades
def _manager_with_attendant_role(app):
    add_user(app, email=DEFAULT_MANAGER_EMAIL, role=UserRole.ATTENDANT)


def _manager_inactive(app):
    add_user(app, email=DEFAULT_MANAGER_EMAIL, role=UserRole.ADMIN, active=False)


def _manager_email_other_case(app):
    add_user(app, email=DEFAULT_MANAGER_EMAIL.upper(), role=UserRole.ATTENDANT)


def _attendant_with_admin_role(app):
    add_user(app, email=DEFAULT_ATTENDANT_EMAIL, role=UserRole.ADMIN)


def _attendant_inactive(app):
    add_counter(app, 1)
    add_user(app, email=DEFAULT_ATTENDANT_EMAIL, role=UserRole.ATTENDANT, active=False, counters=(1,))


def _attendant_without_counter_permission(app):
    add_counter(app, 1)
    add_counter(app, 2)
    add_user(app, email=DEFAULT_ATTENDANT_EMAIL, role=UserRole.ATTENDANT, counters=(2,))


def _counter_inactive(app):
    add_counter(app, 1, active=False)


@pytest.mark.parametrize(
    "setup",
    [
        _manager_with_attendant_role,
        _manager_inactive,
        _manager_email_other_case,
        _attendant_with_admin_role,
        _attendant_inactive,
        _attendant_without_counter_permission,
        _counter_inactive,
    ],
)
def test_incompatible_existing_data_fails_without_mutation(demo_app, run_seed, db_snapshot, passwords_env, no_prompt, setup):
    setup(demo_app)
    before = db_snapshot()

    result = run_seed("--confirm-demo")

    assert result.exit_code != 0
    assert "Execução abortada" in result.output and NO_CHANGES in result.output
    assert db_snapshot() == before  # inclui hash de senha, perfil, situação e permissões


# ------------------------------------------------------------------ validação
@pytest.mark.parametrize(
    "bad_password",
    ["curta1", "SomenteLetras", "1234567890", " Espaco1234", "Espaco1234 ", "atendente.demo99", "A1" * 65],
)
def test_weak_or_invalid_password_is_rejected_without_mutation(run_seed, db_snapshot, passwords_env, monkeypatch, no_prompt, bad_password):
    monkeypatch.setenv(ATTENDANT_PASSWORD_ENV, bad_password)
    before = db_snapshot()
    result = run_seed("--confirm-demo")
    assert result.exit_code != 0
    assert "rejeitada" in result.output
    assert db_snapshot() == before


def test_same_password_for_both_accounts_is_rejected(run_seed, db_snapshot, monkeypatch, no_prompt):
    monkeypatch.setenv(MANAGER_PASSWORD_ENV, MANAGER_PW)
    monkeypatch.setenv(ATTENDANT_PASSWORD_ENV, MANAGER_PW)
    before = db_snapshot()
    result = run_seed("--confirm-demo")
    assert result.exit_code != 0
    assert db_snapshot() == before


def test_prompt_mismatch_fails_without_mutation(run_seed, db_snapshot, monkeypatch):
    answers = iter([MANAGER_PW, "Diferente-123"])
    monkeypatch.setattr(getpass, "getpass", lambda *_a, **_k: next(answers))
    before = db_snapshot()
    result = run_seed("--confirm-demo")
    assert result.exit_code != 0
    assert "não conferem" in result.output
    assert db_snapshot() == before


@pytest.mark.parametrize(
    "args",
    [
        ("--manager-email", "invalido"),
        ("--attendant-email", "sem-dominio@"),
        ("--manager-name", "A"),
        ("--attendant-email", DEFAULT_MANAGER_EMAIL),
        ("--counter", "0"),
        ("--counter", "100"),
    ],
)
def test_invalid_arguments_are_rejected_without_mutation(run_seed, db_snapshot, passwords_env, no_prompt, args):
    before = db_snapshot()
    result = run_seed("--confirm-demo", *args)
    assert result.exit_code != 0
    assert db_snapshot() == before


# ------------------------------------------------------------------ atomicidade
def test_failure_mid_transaction_rolls_back_everything(run_seed, db_snapshot, passwords_env, no_prompt, monkeypatch):
    original = demo_seed.AuditService.record

    def failing_record(action, entity, entity_id=None, **kwargs):
        # falha depois que o guichê e o gestor já foram adicionados à transação
        if action == "DEMO_SEED_USER_CREATED" and (kwargs.get("details") or {}).get("role") == "ATTENDANT":
            raise RuntimeError("falha simulada no meio da transação")
        return original(action, entity, entity_id, **kwargs)

    monkeypatch.setattr(demo_seed.AuditService, "record", staticmethod(failing_record))
    before = db_snapshot()

    result = run_seed("--confirm-demo")

    assert result.exit_code != 0
    assert isinstance(result.exception, RuntimeError)
    assert db_snapshot() == before  # nem guichê, nem gestor, nem auditoria
