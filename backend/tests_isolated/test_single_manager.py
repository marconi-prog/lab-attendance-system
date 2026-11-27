"""Gestor ativo único e gestor-atendente (SQLite temporário — nunca toca o MySQL).

Cobre a restrição no banco (escrita direta), as regras do UserService, a
liberação de guichê em alterações sensíveis e os comandos ``create-admin`` e
``seed-demo``. Os cenários HTTP/concorrência real ficam em ``tests/`` (MySQL).
"""
from __future__ import annotations

import getpass
from datetime import date

import pytest
from sqlalchemy import delete, func, insert, select, text
from sqlalchemy.exc import IntegrityError

from app.cli import register_cli
from app.demo_seed import DEFAULT_MANAGER_EMAIL, MANAGER_PASSWORD_ENV, ATTENDANT_PASSWORD_ENV
from app.extensions import db
from app.models import AuditLog, Call, Counter, CounterSession, Ticket, TicketStatus, TicketType, User, UserRole, user_counters
from app.models.user import is_active_manager_conflict
from app.repositories import UserRepository
from app.schemas.user import UserCreate, UserUpdate
from app.services.attendance_service import AttendanceService
from app.services.user_service import UserService
from app.utils.clock import utcnow
from app.utils.errors import BusinessRuleError, ConflictError, PermissionDenied

PW = "Original-Conta-9"
NEW_PW = "Gestor-Novo-42"


# ------------------------------------------------------------------ apoio
def add_user(app, *, email: str, role: UserRole = UserRole.ATTENDANT, active: bool = True, counters: tuple[int, ...] = ()) -> int:
    with app.app_context():
        user = User(name="Conta pré-existente", email=email, role=role, active=active)
        user.set_password(PW)
        if counters:
            user.counters = list(db.session.scalars(select(Counter).where(Counter.id.in_(counters))))
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        db.session.remove()
        return user_id


def add_counter(app, number: int) -> int:
    with app.app_context():
        counter = Counter(name=f"Guichê {number:02d}", number=number, active=True)
        db.session.add(counter)
        db.session.commit()
        counter_id = counter.id
        db.session.remove()
        return counter_id


def users_state(app) -> list[tuple]:
    with app.app_context():
        rows = db.session.execute(select(User.id, User.email, User.role, User.active, User.password_hash).order_by(User.id)).all()
        db.session.remove()
        return [tuple(r) for r in rows]


def audit_count(app) -> int:
    with app.app_context():
        count = db.session.scalar(select(func.count(AuditLog.id)))
        db.session.remove()
        return count


def raw_insert_admin(email: str, active: bool = True):
    db.session.execute(
        insert(User).values(
            name="Escrita direta", email=email, password_hash="hash-fake", role=UserRole.ADMIN, active=active,
            created_at=utcnow(), updated_at=utcnow(),
        )
    )
    db.session.commit()


@pytest.fixture()
def manager(demo_app) -> int:
    return add_user(demo_app, email="gestor@lab.test", role=UserRole.ADMIN)


@pytest.fixture()
def no_precheck(monkeypatch):
    """Simula a corrida: a verificação prévia não enxerga o outro gestor (ainda não confirmado)."""
    monkeypatch.setattr(UserRepository, "active_manager", staticmethod(lambda **_kwargs: None))


# ------------------------------------------------------------------ banco (escrita direta)
def test_database_allows_one_active_manager_plus_inactive_admins_and_attendants(demo_app, manager):
    add_user(demo_app, email="antigo1@lab.test", role=UserRole.ADMIN, active=False)
    add_user(demo_app, email="antigo2@lab.test", role=UserRole.ADMIN, active=False)
    add_user(demo_app, email="a1@lab.test")
    add_user(demo_app, email="a2@lab.test", active=False)
    with demo_app.app_context():
        slots = dict(db.session.execute(select(User.email, User.active_manager_slot)).all())
        assert slots == {"gestor@lab.test": 1, "antigo1@lab.test": None, "antigo2@lab.test": None,
                         "a1@lab.test": None, "a2@lab.test": None}


def test_database_rejects_second_active_manager_on_direct_insert(demo_app, manager):
    before = users_state(demo_app)
    with demo_app.app_context():
        with pytest.raises(IntegrityError) as exc:
            raw_insert_admin("intruso@lab.test")
        assert is_active_manager_conflict(exc.value)
        db.session.rollback()
        raw_insert_admin("inativo@lab.test", active=False)  # ADMIN inativo continua permitido
    assert len(users_state(demo_app)) == len(before) + 1


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE users SET role = 'ADMIN' WHERE email = 'atendente@lab.test'",  # promoção direta
        "UPDATE users SET active = 1 WHERE email = 'antigo@lab.test'",  # reativação direta
    ],
)
def test_database_rejects_direct_promotion_or_reactivation(demo_app, manager, statement):
    add_user(demo_app, email="atendente@lab.test")
    add_user(demo_app, email="antigo@lab.test", role=UserRole.ADMIN, active=False)
    before = users_state(demo_app)
    with demo_app.app_context():
        with pytest.raises(IntegrityError) as exc:
            db.session.execute(text(statement))
            db.session.commit()
        assert is_active_manager_conflict(exc.value)
        db.session.rollback()
    assert users_state(demo_app) == before


def test_conflict_detector_ignores_other_integrity_errors(demo_app, manager):
    with demo_app.app_context():
        with pytest.raises(IntegrityError) as exc:
            db.session.execute(insert(User).values(name="Dup", email="gestor@lab.test", password_hash="x",
                                                   role=UserRole.ATTENDANT, active=True, created_at=utcnow(), updated_at=utcnow()))
        assert not is_active_manager_conflict(exc.value)
        db.session.rollback()


# ------------------------------------------------------------------ UserService (regras da API)
def _create(role: UserRole, email: str = "novo@lab.test") -> UserCreate:
    return UserCreate(name="Nova Conta", email=email, password="Segura123", role=role)


def test_create_second_manager_is_conflict_409(demo_app, manager):
    before, audits = users_state(demo_app), audit_count(demo_app)
    with demo_app.app_context():
        actor = db.session.get(User, manager)
        with pytest.raises(ConflictError) as exc:
            UserService.create(_create(UserRole.ADMIN), actor=actor)
        assert exc.value.status_code == 409 and exc.value.code == "ACTIVE_MANAGER_EXISTS"
        assert "apenas um gestor ativo" in exc.value.message
        UserService.create(_create(UserRole.ATTENDANT), actor=actor)  # atendentes continuam livres
    assert len(users_state(demo_app)) == len(before) + 1
    assert audit_count(demo_app) == audits + 1


@pytest.mark.parametrize(
    ("target", "changes"),
    [
        ("attendant", {"role": UserRole.ADMIN}),  # promoção
        ("old_manager", {"active": True}),  # reativação de gestor antigo
        ("inactive_attendant", {"role": UserRole.ADMIN, "active": True}),  # promoção + reativação
    ],
)
def test_promote_or_reactivate_while_manager_exists_is_conflict(demo_app, manager, target, changes):
    ids = {
        "attendant": add_user(demo_app, email="atendente@lab.test"),
        "old_manager": add_user(demo_app, email="antigo@lab.test", role=UserRole.ADMIN, active=False),
        "inactive_attendant": add_user(demo_app, email="inativo@lab.test", active=False),
    }
    before, audits = users_state(demo_app), audit_count(demo_app)
    with demo_app.app_context():
        actor = db.session.get(User, manager)
        with pytest.raises(ConflictError) as exc:
            UserService.update(ids[target], UserUpdate(**changes), actor=actor)
        assert exc.value.code == "ACTIVE_MANAGER_EXISTS"
    assert users_state(demo_app) == before
    assert audit_count(demo_app) == audits


def test_database_constraint_catches_race_and_rolls_back(demo_app, manager, no_precheck):
    attendant = add_user(demo_app, email="atendente@lab.test")
    before, audits = users_state(demo_app), audit_count(demo_app)
    with demo_app.app_context():
        actor = db.session.get(User, manager)
        with pytest.raises(ConflictError) as created:
            UserService.create(_create(UserRole.ADMIN), actor=actor)
        with pytest.raises(ConflictError) as promoted:
            UserService.update(attendant, UserUpdate(role=UserRole.ADMIN), actor=actor)
        assert created.value.code == promoted.value.code == "ACTIVE_MANAGER_EXISTS"
        # a sessão continua utilizável após o rollback
        assert db.session.get(User, attendant).role == UserRole.ATTENDANT
    assert users_state(demo_app) == before
    assert audit_count(demo_app) == audits


def test_old_manager_may_be_reactivated_as_attendant(demo_app, manager):
    old = add_user(demo_app, email="antigo@lab.test", role=UserRole.ADMIN, active=False)
    with demo_app.app_context():
        actor = db.session.get(User, manager)
        user = UserService.update(old, UserUpdate(role=UserRole.ATTENDANT, active=True), actor=actor)
        assert (user.role, user.active) == (UserRole.ATTENDANT, True)


def test_promotion_allowed_when_no_active_manager(demo_app):
    actor_id = add_user(demo_app, email="operador@lab.test")
    target = add_user(demo_app, email="futuro@lab.test")
    with demo_app.app_context():
        user = UserService.update(target, UserUpdate(role=UserRole.ADMIN), actor=db.session.get(User, actor_id))
        assert user.role == UserRole.ADMIN and user.active_manager_slot == 1


def test_manager_editing_self_keeps_role_and_self_lockout_is_preserved(demo_app, manager):
    with demo_app.app_context():
        actor = db.session.get(User, manager)
        assert UserService.update(manager, UserUpdate(name="Gestora Renomeada", role=UserRole.ADMIN), actor=actor).name == "Gestora Renomeada"
        for changes in ({"active": False}, {"role": UserRole.ATTENDANT}):
            with pytest.raises(BusinessRuleError) as exc:
                UserService.update(manager, UserUpdate(**changes), actor=actor)
            assert exc.value.code == "SELF_LOCKOUT"


# ------------------------------------------------------------------ sessões de guichê
def _open_session(app, user_id: int, counter_id: int) -> int:
    with app.app_context():
        session = AttendanceService.open_session(db.session.get(User, user_id), counter_id)
        session_id = session.id
        db.session.remove()
        return session_id


def _session_closed(app, session_id: int) -> bool:
    with app.app_context():
        closed = db.session.get(CounterSession, session_id).closed_at is not None
        db.session.remove()
        return closed


def _put_ticket_on_counter(app, user_id: int, counter_id: int) -> None:
    with app.app_context():
        ticket = Ticket(code="261110-SG001", type=TicketType.SG, status=TicketStatus.CHAMADA, daily_sequence=1,
                        reference_date=date(2026, 11, 10))
        db.session.add(ticket)
        db.session.flush()
        db.session.add(Call(ticket_id=ticket.id, user_id=user_id, counter_id=counter_id, attempt_number=1, called_at=utcnow()))
        db.session.commit()
        db.session.remove()


def test_manager_opens_only_assigned_counters(demo_app, manager):
    assigned, other = add_counter(demo_app, 1), add_counter(demo_app, 2)
    with demo_app.app_context():
        user = db.session.get(User, manager)
        user.counters = [db.session.get(Counter, assigned)]
        db.session.commit()
        with pytest.raises(PermissionDenied) as exc:
            AttendanceService.open_session(user, other)
        assert exc.value.code == "COUNTER_NOT_AUTHORIZED"
        assert AttendanceService.open_session(user, assigned).counter_id == assigned


def test_deactivating_user_closes_open_counter_session(demo_app, manager):
    counter = add_counter(demo_app, 1)
    attendant = add_user(demo_app, email="atendente@lab.test", counters=(counter,))
    session_id = _open_session(demo_app, attendant, counter)
    with demo_app.app_context():
        UserService.update(attendant, UserUpdate(active=False), actor=db.session.get(User, manager))
        log = db.session.scalars(select(AuditLog).where(AuditLog.action == "COUNTER_SESSION_FORCE_CLOSED")).one()
        assert log.user_id == manager and log.details["reason"] == "USER_DEACTIVATED"
    assert _session_closed(demo_app, session_id)


def test_deactivation_refused_while_ticket_in_progress(demo_app, manager):
    counter = add_counter(demo_app, 1)
    attendant = add_user(demo_app, email="atendente@lab.test", counters=(counter,))
    session_id = _open_session(demo_app, attendant, counter)
    _put_ticket_on_counter(demo_app, attendant, counter)
    before = users_state(demo_app)
    with demo_app.app_context():
        with pytest.raises(ConflictError) as exc:
            UserService.update(attendant, UserUpdate(active=False), actor=db.session.get(User, manager))
        assert exc.value.code == "ACTIVE_TICKET_PENDING"
    assert users_state(demo_app) == before
    assert not _session_closed(demo_app, session_id)


def test_removing_session_counter_closes_session_but_keeping_it_does_not(demo_app, manager):
    c1, c2 = add_counter(demo_app, 1), add_counter(demo_app, 2)
    attendant = add_user(demo_app, email="atendente@lab.test", counters=(c1, c2))
    session_id = _open_session(demo_app, attendant, c1)
    with demo_app.app_context():
        actor = db.session.get(User, manager)
        UserService.assign_counters(attendant, [c1], actor=actor)
    assert not _session_closed(demo_app, session_id)
    with demo_app.app_context():
        UserService.assign_counters(attendant, [c2], actor=db.session.get(User, manager))
    assert _session_closed(demo_app, session_id)


def test_operation_requires_counter_still_authorized(demo_app, manager):
    counter = add_counter(demo_app, 1)
    with demo_app.app_context():
        user = db.session.get(User, manager)
        user.counters = [db.session.get(Counter, counter)]
        db.session.commit()
    _open_session(demo_app, manager, counter)
    with demo_app.app_context():
        db.session.execute(delete(user_counters))  # revogação por escrita direta
        db.session.commit()
        with pytest.raises(PermissionDenied) as exc:
            AttendanceService.require_session(db.session.get(User, manager))
        assert exc.value.code == "COUNTER_NOT_AUTHORIZED"


# ------------------------------------------------------------------ flask create-admin
@pytest.fixture()
def run_create_admin(demo_app, monkeypatch):
    register_cli(demo_app)
    monkeypatch.setenv("ADMIN_PASSWORD", NEW_PW)

    def _run(email: str = "novo.gestor@lab.test"):
        return demo_app.test_cli_runner().invoke(args=["create-admin", "--name", "Novo Gestor", "--email", email])

    return _run


@pytest.fixture()
def no_prompt(monkeypatch):
    def _fail(*_args, **_kwargs):
        raise AssertionError("o comando não deveria pedir senha neste cenário")

    monkeypatch.setattr(getpass, "getpass", _fail)


def test_create_admin_creates_first_manager(demo_app, run_create_admin):
    add_user(demo_app, email="antigo@lab.test", role=UserRole.ADMIN, active=False)  # inativo não bloqueia
    result = run_create_admin()
    assert result.exit_code == 0, result.output
    with demo_app.app_context():
        assert UserRepository.active_manager().email == "novo.gestor@lab.test"


def test_create_admin_refuses_when_active_manager_exists(demo_app, manager, run_create_admin, no_prompt, monkeypatch):
    monkeypatch.delenv("ADMIN_PASSWORD")  # recusa antes de pedir senha
    before = users_state(demo_app)
    result = run_create_admin()
    assert result.exit_code != 0
    assert "gestor ativo" in result.output and "Nenhum dado foi alterado" in result.output
    assert users_state(demo_app) == before


def test_create_admin_race_is_reported_clearly_and_rolled_back(demo_app, manager, run_create_admin, no_precheck):
    before = users_state(demo_app)
    result = run_create_admin()
    assert result.exit_code != 0
    assert "gestor ativo" in result.output and "Nenhum dado foi alterado" in result.output
    assert not isinstance(result.exception, IntegrityError)
    assert users_state(demo_app) == before


# ------------------------------------------------------------------ flask seed-demo
@pytest.fixture()
def seed_passwords(monkeypatch):
    monkeypatch.setenv(MANAGER_PASSWORD_ENV, "Painel-Teste-41")
    monkeypatch.setenv(ATTENDANT_PASSWORD_ENV, "Guiche-Teste-73")


def test_seed_demo_aborts_when_another_active_manager_exists(demo_app, run_seed, db_snapshot, seed_passwords, no_prompt):
    add_user(demo_app, email="gestor.real@lab.test", role=UserRole.ADMIN)
    before = db_snapshot()
    result = run_seed("--confirm-demo")
    assert result.exit_code != 0
    assert "Execução abortada" in result.output and "gestor ativo" in result.output
    assert "Nenhum dado foi alterado" in result.output
    assert db_snapshot() == before  # nada criado: nem guichê, nem atendente


def test_seed_demo_reuses_the_existing_manager_when_pointed_to_it(demo_app, run_seed, seed_passwords):
    add_user(demo_app, email="gestor.real@lab.test", role=UserRole.ADMIN)
    result = run_seed("--confirm-demo", "--manager-email", "gestor.real@lab.test")
    assert result.exit_code == 0, result.output
    with demo_app.app_context():
        assert UserRepository.active_manager().email == "gestor.real@lab.test"
        assert db.session.scalar(select(func.count(User.id)).where(User.role == UserRole.ADMIN)) == 1


def test_seed_demo_ignores_inactive_admins(demo_app, run_seed, seed_passwords):
    add_user(demo_app, email="antigo@lab.test", role=UserRole.ADMIN, active=False)
    result = run_seed("--confirm-demo")
    assert result.exit_code == 0, result.output
    with demo_app.app_context():
        assert UserRepository.active_manager().email == DEFAULT_MANAGER_EMAIL


def test_seed_demo_race_rolls_back_everything(demo_app, run_seed, db_snapshot, seed_passwords, no_precheck):
    add_user(demo_app, email="gestor.real@lab.test", role=UserRole.ADMIN)
    before = db_snapshot()
    result = run_seed("--confirm-demo")
    assert result.exit_code != 0
    assert "gestor ativo" in result.output and "Nenhum dado foi alterado" in result.output
    assert db_snapshot() == before
