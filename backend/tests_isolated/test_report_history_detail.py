"""ReportService.history — campos de ATENDIMENTO só existem para senhas atendidas.

Regra (documento principal, p. 7): no relatório detalhado, uma senha que nunca
foi atendida (não compareceu, aguardando, descartada ou apenas chamada) não tem
início, fim, duração, guichê nem atendente de atendimento. Os campos de
auditoria das chamadas (first_called_at, last_called_at, call_count) e os
registros de chamada continuam intactos.

SQLite temporário (tmp_path) — nunca toca o MySQL.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from flask import Flask
from sqlalchemy import func, select

from app.extensions import db
from app.models import Attendance, AttendanceResult, AuditLog, Call, Counter, Ticket, TicketStatus, TicketType, User, UserRole
from app.services.report_service import ReportService

DAY = date(2026, 11, 10)
BASE = datetime(2026, 11, 10, 12, 0, 0)  # UTC (09:00 em America/Recife)
ATTENDANCE_FIELDS = ("started_at", "finished_at", "duration_seconds", "attendant", "counter")


@pytest.fixture()
def history_app(tmp_path):
    app = Flask("history_isolated")
    app.config.update(
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{(tmp_path / 'history.sqlite').as_posix()}",
        TIMEZONE="America/Recife",
        TESTING=True,
    )
    assert app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:///"), "teste isolado deve usar SQLite"
    db.init_app(app)
    with app.app_context():
        db.create_all()
        _populate()
        yield app
        db.session.remove()
        db.engine.dispose()


def _user(name: str, email: str) -> User:
    user = User(name=name, email=email, role=UserRole.ATTENDANT, active=True)
    user.set_password("Fixture-Only-123")
    db.session.add(user)
    return user


def _ticket(seq: int, ticket_type: TicketType, status: TicketStatus, minute: int) -> Ticket:
    ticket = Ticket(
        code=f"261110-{ticket_type.value}{seq:03d}", type=ticket_type, status=status, daily_sequence=seq,
        reference_date=DAY, issued_at=BASE + timedelta(minutes=minute),
    )
    db.session.add(ticket)
    db.session.flush()
    return ticket


def _call(ticket: Ticket, user: User, counter: Counter, attempt: int, minute: int) -> None:
    db.session.add(Call(ticket_id=ticket.id, user_id=user.id, counter_id=counter.id, attempt_number=attempt,
                        called_at=BASE + timedelta(minutes=minute)))


def _populate() -> None:
    caller = _user("Atendente que chamou", "chamou@fixture.local")
    server = _user("Atendente que atendeu", "atendeu@fixture.local")
    counter_1 = Counter(name="Guichê 01", number=1, active=True)
    counter_2 = Counter(name="Guichê 02", number=2, active=True)
    db.session.add_all([counter_1, counter_2])
    db.session.flush()

    # ATENDIDA após 2 chamadas: atendimento registrado em outro guichê/atendente que a última chamada
    # (cenário artificial, só para provar que os campos de atendimento vêm de Attendance).
    done = _ticket(1, TicketType.SP, TicketStatus.ATENDIDA, 0)
    _call(done, caller, counter_2, 1, 5)
    _call(done, caller, counter_2, 2, 6)
    db.session.add(Attendance(ticket_id=done.id, user_id=server.id, counter_id=counter_1.id,
                              started_at=BASE + timedelta(minutes=7), finished_at=BASE + timedelta(minutes=17),
                              duration_seconds=600, result=AttendanceResult.CONCLUIDO))

    # NAO_COMPARECEU: duas chamadas, nunca atendida.
    absent = _ticket(2, TicketType.SP, TicketStatus.NAO_COMPARECEU, 1)
    _call(absent, caller, counter_2, 1, 8)
    _call(absent, caller, counter_2, 2, 9)

    # CHAMADA: chamada uma vez, atendimento ainda não iniciado.
    called = _ticket(1, TicketType.SE, TicketStatus.CHAMADA, 2)
    _call(called, caller, counter_2, 1, 10)

    # EM_ATENDIMENTO: iniciado, ainda sem fim.
    running = _ticket(1, TicketType.SG, TicketStatus.EM_ATENDIMENTO, 3)
    _call(running, server, counter_1, 1, 11)
    db.session.add(Attendance(ticket_id=running.id, user_id=server.id, counter_id=counter_1.id,
                              started_at=BASE + timedelta(minutes=12), result=AttendanceResult.EM_ANDAMENTO))

    # AGUARDANDO e DESCARTADA: nunca chamadas.
    _ticket(2, TicketType.SG, TicketStatus.AGUARDANDO, 4)
    _ticket(3, TicketType.SG, TicketStatus.DESCARTADA, 5)

    db.session.add(AuditLog(action="TICKET_CALLED", entity="ticket", entity_id=str(absent.id), user_id=caller.id))
    db.session.commit()


def _rows(status: TicketStatus | None = None) -> dict[str, dict]:
    rows, _total = ReportService.history(DAY, DAY, None, status, 1, 50)
    return {row["code"]: row for row in rows}


def _snapshot() -> tuple:
    return tuple(db.session.scalar(select(func.count()).select_from(t)) for t in db.metadata.sorted_tables)


def test_no_show_has_call_audit_but_no_attendance_fields(history_app):
    row = _rows()["261110-SP002"]
    assert row["status"] == "NAO_COMPARECEU"
    assert {field: row[field] for field in ATTENDANCE_FIELDS} == dict.fromkeys(ATTENDANCE_FIELDS)
    # auditoria das chamadas preservada
    assert row["call_count"] == 2
    assert row["first_called_at"] == "2026-11-10T09:08:00-03:00"
    assert row["last_called_at"] == "2026-11-10T09:09:00-03:00"


def test_called_but_not_started_has_no_attendance_fields(history_app):
    row = _rows()["261110-SE001"]
    assert row["status"] == "CHAMADA"
    assert {field: row[field] for field in ATTENDANCE_FIELDS} == dict.fromkeys(ATTENDANCE_FIELDS)
    assert (row["call_count"], row["first_called_at"]) == (1, "2026-11-10T09:10:00-03:00")


@pytest.mark.parametrize(("code", "status"), [("261110-SG002", "AGUARDANDO"), ("261110-SG003", "DESCARTADA")])
def test_never_called_tickets_are_blank(history_app, code, status):
    row = _rows()[code]
    assert row["status"] == status
    assert {field: row[field] for field in ATTENDANCE_FIELDS} == dict.fromkeys(ATTENDANCE_FIELDS)
    assert (row["call_count"], row["first_called_at"], row["last_called_at"]) == (0, None, None)


def test_completed_ticket_uses_attendance_counter_and_attendant(history_app):
    row = _rows()["261110-SP001"]
    assert row["status"] == "ATENDIDA"
    assert row["started_at"] == "2026-11-10T09:07:00-03:00"
    assert row["finished_at"] == "2026-11-10T09:17:00-03:00"
    assert row["duration_seconds"] == 600
    assert row["attendant"]["name"] == "Atendente que atendeu"
    assert row["counter"]["number"] == 1  # guichê do atendimento, não o da última chamada (02)
    assert (row["call_count"], row["last_called_at"]) == (2, "2026-11-10T09:06:00-03:00")


def test_in_progress_ticket_shows_started_attendance(history_app):
    row = _rows()["261110-SG001"]
    assert row["status"] == "EM_ATENDIMENTO"
    assert row["started_at"] == "2026-11-10T09:12:00-03:00"
    assert (row["finished_at"], row["duration_seconds"]) == (None, None)
    assert row["attendant"]["name"] == "Atendente que atendeu"
    assert row["counter"]["number"] == 1


def test_status_filter_and_report_is_read_only(history_app):
    before = _snapshot()
    rows, total = ReportService.history(DAY, DAY, None, TicketStatus.NAO_COMPARECEU, 1, 50)
    assert total == 1 and [r["code"] for r in rows] == ["261110-SP002"]
    assert rows[0]["counter"] is None and rows[0]["attendant"] is None
    assert len(_rows()) == 6
    assert _snapshot() == before  # chamadas e auditoria intactas
    assert db.session.scalar(select(func.count(Call.id))) == 6
    assert db.session.scalar(select(func.count(AuditLog.id))) == 1
