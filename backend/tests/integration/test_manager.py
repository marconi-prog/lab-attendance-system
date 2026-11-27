"""Gestor como atendente com capacidades de administração + gestor ativo único."""
import threading

import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models import Attendance, AuditLog, User, UserRole
from app.repositories import UserRepository
from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import UserService
from app.utils.errors import ConflictError
from tests.conftest import login


@pytest.fixture()
def manager(client, make_user, make_counter):
    """Gestor (ADMIN) autenticado, autorizado em um guichê, sem sessão aberta."""
    counter_id = make_counter()
    user = make_user(UserRole.ADMIN, [counter_id])
    return {"user": user, "headers": login(client, user), "counter_id": counter_id}


def post(client, h, ticket_id, action):
    return client.post(f"/api/attendant/tickets/{ticket_id}/{action}", headers=h)


def active_managers(app) -> list[int]:
    with app.app_context():
        return list(db.session.scalars(select(User.id).where(User.role == UserRole.ADMIN, User.active.is_(True))))


# ------------------------------------------------------------ gestor atendendo
def test_manager_operates_assigned_counter_end_to_end(client, manager, issue, clock, app):
    h, counter_id = manager["headers"], manager["counter_id"]
    available = client.get("/api/attendant/counters", headers=h).json["items"]
    assert [item["counter"]["id"] for item in available] == [counter_id]
    assert client.post("/api/attendant/session", json={"counter_id": counter_id}, headers=h).status_code == 201

    issue("SP")
    issue("SG")
    first = client.post("/api/attendant/call-next", headers=h)
    assert first.status_code == 200 and first.json["ticket"]["short_code"] == "SP001"
    ticket_id = first.json["ticket"]["id"]
    assert post(client, h, ticket_id, "start").json["ticket"]["status"] == "EM_ATENDIMENTO"
    clock.advance(minutes=2)
    finished = post(client, h, ticket_id, "finish")
    assert finished.status_code == 200 and finished.json["attendance"]["duration_seconds"] == 120

    second = client.post("/api/attendant/call-next", headers=h).json["ticket"]["id"]
    assert post(client, h, second, "recall").status_code == 200
    assert post(client, h, second, "no-show").json["ticket"]["status"] == "NAO_COMPARECEU"

    state = client.get("/api/attendant/state", headers=h).json
    assert state["session"]["counter"]["id"] == counter_id and state["user"]["id"] == manager["user"]["id"]
    with app.app_context():
        attendance = db.session.scalar(select(Attendance))
        assert (attendance.user_id, attendance.counter_id) == (manager["user"]["id"], counter_id)
    # continua gestor: as rotas de gestão seguem liberadas durante o atendimento
    assert client.get("/api/admin/dashboard", headers=h).status_code == 200
    assert client.get("/api/counters/sessions", headers=h).json["items"][0]["user"]["id"] == manager["user"]["id"]
    assert client.delete("/api/attendant/session", headers=h).status_code == 204


def test_manager_cannot_use_unassigned_counter_nor_other_counters_ticket(client, manager, make_user, make_counter, issue):
    h = manager["headers"]
    other_counter = make_counter()
    denied = client.post("/api/attendant/session", json={"counter_id": other_counter}, headers=h)
    assert denied.status_code == 403 and denied.json["error"]["code"] == "COUNTER_NOT_AUTHORIZED"
    no_session = client.post("/api/attendant/call-next", headers=h)
    assert no_session.status_code == 422 and no_session.json["error"]["code"] == "NO_COUNTER_SESSION"

    attendant = login(client, make_user(UserRole.ATTENDANT, [other_counter]))
    assert client.post("/api/attendant/session", json={"counter_id": other_counter}, headers=attendant).status_code == 201
    issue("SG")
    ticket_id = client.post("/api/attendant/call-next", headers=attendant).json["ticket"]["id"]
    assert client.post("/api/attendant/session", json={"counter_id": manager["counter_id"]}, headers=h).status_code == 201
    for action in ("start", "recall", "finish", "no-show"):
        response = post(client, h, ticket_id, action)
        assert response.status_code == 403 and response.json["error"]["code"] == "TICKET_NOT_OWNED"


def test_manager_assigns_counter_to_self_and_losing_it_releases_the_counter(client, admin_headers, make_counter):
    me = client.get("/api/auth/me", headers=admin_headers).json
    counter_id = make_counter()
    assert client.get("/api/attendant/counters", headers=admin_headers).json["items"] == []
    assigned = client.put(f"/api/users/{me['id']}/counters", json={"counter_ids": [counter_id]}, headers=admin_headers)
    assert assigned.status_code == 200 and [c["id"] for c in assigned.json["counters"]] == [counter_id]
    assert client.post("/api/attendant/session", json={"counter_id": counter_id}, headers=admin_headers).status_code == 201

    assert client.put(f"/api/users/{me['id']}/counters", json={"counter_ids": []}, headers=admin_headers).status_code == 200
    assert client.get("/api/attendant/state", headers=admin_headers).json["session"] is None


def test_deactivation_releases_counter_but_never_with_ticket_in_progress(client, admin_headers, attendant, issue):
    user_id, h = attendant["user"]["id"], attendant["headers"]
    issue("SG")
    ticket_id = client.post("/api/attendant/call-next", headers=h).json["ticket"]["id"]
    blocked = client.patch(f"/api/users/{user_id}", json={"active": False}, headers=admin_headers)
    assert blocked.status_code == 409 and blocked.json["error"]["code"] == "ACTIVE_TICKET_PENDING"
    assert client.get("/api/auth/me", headers=h).status_code == 200  # nada mudou

    assert post(client, h, ticket_id, "start").status_code == 200
    assert post(client, h, ticket_id, "finish").status_code == 200
    assert client.patch(f"/api/users/{user_id}", json={"active": False}, headers=admin_headers).status_code == 200
    assert client.get("/api/counters/sessions", headers=admin_headers).json["items"] == []


# ------------------------------------------------------------ gestor ativo único (API)
def test_api_refuses_second_active_manager(client, admin_headers, make_user, app):
    attendant = make_user()
    old_manager = make_user(UserRole.ADMIN, active=False)
    payload = {"name": "Outro Gestor", "email": "outro@lab.test", "password": "Segura123", "role": "ADMIN"}
    attempts = [
        client.post("/api/users", json=payload, headers=admin_headers),
        client.patch(f"/api/users/{attendant['id']}", json={"role": "ADMIN"}, headers=admin_headers),
        client.patch(f"/api/users/{old_manager['id']}", json={"active": True}, headers=admin_headers),
    ]
    for response in attempts:
        assert response.status_code == 409, response.json
        assert response.json["error"]["code"] == "ACTIVE_MANAGER_EXISTS"
        assert "apenas um gestor ativo" in response.json["error"]["message"]
    assert len(active_managers(app)) == 1
    with app.app_context():
        assert db.session.scalar(select(func.count(AuditLog.id)).where(AuditLog.action.like("USER_%"))) == 0

    # o gestor antigo pode voltar como atendente; ninguém é rebaixado automaticamente
    back = client.patch(f"/api/users/{old_manager['id']}", json={"role": "ATTENDANT", "active": True}, headers=admin_headers)
    assert back.status_code == 200 and back.json["role"] == "ATTENDANT"


def test_api_race_is_still_409_when_precheck_misses_the_other_manager(client, admin_headers, make_user, monkeypatch, app):
    attendant = make_user()
    monkeypatch.setattr(UserRepository, "active_manager", staticmethod(lambda **_kwargs: None))
    payload = {"name": "Outro Gestor", "email": "outro@lab.test", "password": "Segura123", "role": "ADMIN"}
    for response in (
        client.post("/api/users", json=payload, headers=admin_headers),
        client.patch(f"/api/users/{attendant['id']}", json={"role": "ADMIN"}, headers=admin_headers),
    ):
        assert response.status_code == 409 and response.json["error"]["code"] == "ACTIVE_MANAGER_EXISTS"
    assert len(active_managers(app)) == 1


def _run_concurrently(app, monkeypatch, operation) -> list[str]:
    """Executa `operation(n)` em duas threads que passam juntas pela verificação prévia."""
    barrier = threading.Barrier(2, timeout=15)
    real = UserRepository.active_manager

    def synced(**kwargs):
        found = real(**kwargs)
        barrier.wait()  # ambas viram "nenhum gestor ativo" antes de qualquer gravação
        return found

    monkeypatch.setattr(UserRepository, "active_manager", staticmethod(synced))
    results: list[str] = []

    def worker(n: int) -> None:
        with app.app_context():
            try:
                operation(n)
                results.append("ok")
            except ConflictError as exc:
                results.append(exc.code)
            except Exception as exc:  # noqa: BLE001 — registrado para a asserção
                results.append(repr(exc))
            finally:
                db.session.remove()

    threads = [threading.Thread(target=worker, args=(n,)) for n in (1, 2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    return sorted(results)


def test_concurrent_manager_creation_allows_exactly_one(app, make_user, monkeypatch):
    actor_id = make_user()["id"]  # sem gestor ativo no início

    def create(n: int) -> None:
        data = UserCreate(name=f"Gestor {n}", email=f"gestor{n}@lab.test", password="Segura123", role=UserRole.ADMIN)
        UserService.create(data, actor=db.session.get(User, actor_id))

    assert _run_concurrently(app, monkeypatch, create) == ["ACTIVE_MANAGER_EXISTS", "ok"]
    assert len(active_managers(app)) == 1


def test_concurrent_promotion_allows_exactly_one(app, make_user, monkeypatch):
    actor_id = make_user()["id"]
    targets = {1: make_user()["id"], 2: make_user()["id"]}

    def promote(n: int) -> None:
        UserService.update(targets[n], UserUpdate(role=UserRole.ADMIN), actor=db.session.get(User, actor_id))

    assert _run_concurrently(app, monkeypatch, promote) == ["ACTIVE_MANAGER_EXISTS", "ok"]
    assert len(active_managers(app)) == 1


def test_concurrent_reactivation_allows_exactly_one(app, make_user, monkeypatch):
    actor_id = make_user()["id"]
    targets = {1: make_user(UserRole.ADMIN, active=False)["id"], 2: make_user(UserRole.ADMIN, active=False)["id"]}

    def reactivate(n: int) -> None:
        UserService.update(targets[n], UserUpdate(active=True), actor=db.session.get(User, actor_id))

    assert _run_concurrently(app, monkeypatch, reactivate) == ["ACTIVE_MANAGER_EXISTS", "ok"]
    assert len(active_managers(app)) == 1
