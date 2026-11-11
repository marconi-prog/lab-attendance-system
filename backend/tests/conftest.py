"""Fixtures de teste.

Os testes rodam contra um banco MySQL real (TEST_DATABASE_URL), pois as
garantias de concorrência dependem do InnoDB (SELECT ... FOR UPDATE /
SKIP LOCKED). O banco de teste é recriado no início e limpo após cada teste.
"""
from __future__ import annotations

import itertools
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app import create_app
from app.extensions import db as _db
from app.models import Counter, User, UserRole
from app.utils.clock import Clock

RECIFE = ZoneInfo("America/Recife")
PASSWORD = "Senha12345"
_seq = itertools.count(1)


@pytest.fixture(scope="session")
def app():
    application = create_app("testing")
    uri = application.config["SQLALCHEMY_DATABASE_URI"]
    if not uri:
        pytest.exit("Defina TEST_DATABASE_URL (veja backend/.env.example).", returncode=2)
    if "test" not in (make_url(uri).database or ""):
        pytest.exit("Por segurança, o nome do banco de testes deve conter 'test'.", returncode=2)
    with application.app_context():
        _db.drop_all()
        _db.create_all()
    yield application
    with application.app_context():
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(autouse=True)
def _clean_db(app):
    yield
    with app.app_context():
        _db.session.remove()
        with _db.engine.begin() as conn:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            for table in reversed(_db.metadata.sorted_tables):
                # DELETE é muito mais rápido que TRUNCATE para tabelas pequenas no InnoDB
                conn.execute(text(f"DELETE FROM `{table.name}`"))
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


@pytest.fixture()
def ctx(app):
    with app.app_context():
        yield
        _db.session.remove()


@pytest.fixture()
def client(app):
    return app.test_client()


class FrozenClock:
    """Controla o horário 'atual' (informado no fuso America/Recife)."""

    def __init__(self, monkeypatch):
        self.current = datetime(2026, 11, 10, 9, 0, tzinfo=RECIFE)
        monkeypatch.setattr(Clock, "now_utc", staticmethod(lambda: self.current.astimezone(timezone.utc)))

    def set(self, value: str) -> None:
        """Ex.: clock.set('2026-11-10 16:59')"""
        self.current = datetime.strptime(value, "%Y-%m-%d %H:%M").replace(tzinfo=RECIFE)

    def advance(self, **kwargs) -> None:
        from datetime import timedelta

        self.current = self.current + timedelta(**kwargs)


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    return FrozenClock(monkeypatch)


# ------------------------------------------------------------------ fábricas
@pytest.fixture()
def make_counter(app):
    def _make(number: int | None = None, active: bool = True) -> int:
        with app.app_context():
            n = number or next(_seq) % 90 + 1
            while _db.session.query(Counter.id).filter_by(number=n).first():
                n = next(_seq) % 90 + 1
            counter = Counter(name=f"Guichê {n:02d}", number=n, active=active)
            _db.session.add(counter)
            _db.session.commit()
            return counter.id

    return _make


@pytest.fixture()
def make_user(app):
    def _make(role: UserRole = UserRole.ATTENDANT, counter_ids: list[int] | None = None, active: bool = True) -> dict:
        with app.app_context():
            n = next(_seq)
            user = User(name=f"Usuário {n}", email=f"user{n}@lab.test", role=role, active=active)
            user.set_password(PASSWORD)
            if counter_ids:
                user.counters = _db.session.query(Counter).filter(Counter.id.in_(counter_ids)).all()
            _db.session.add(user)
            _db.session.commit()
            return {"id": user.id, "email": user.email, "password": PASSWORD}

    return _make


def login(client, user: dict) -> dict:
    response = client.post("/api/auth/login", json={"email": user["email"], "password": user["password"]})
    assert response.status_code == 200, response.json
    return {"Authorization": f"Bearer {response.json['access_token']}"}


@pytest.fixture()
def admin_headers(client, make_user):
    return login(client, make_user(UserRole.ADMIN))


@pytest.fixture()
def attendant(client, make_user, make_counter):
    """Atendente autenticado com guichê já aberto."""
    counter_id = make_counter()
    user = make_user(UserRole.ATTENDANT, [counter_id])
    headers = login(client, user)
    response = client.post("/api/attendant/session", json={"counter_id": counter_id}, headers=headers)
    assert response.status_code == 201, response.json
    return {"user": user, "headers": headers, "counter_id": counter_id}


@pytest.fixture()
def issue(client):
    def _issue(ticket_type: str) -> dict:
        response = client.post("/api/tickets", json={"type": ticket_type})
        assert response.status_code == 201, response.json
        return response.json["ticket"]

    return _issue
