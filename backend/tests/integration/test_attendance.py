"""Atendimento: início, finalização, repetição e ausência."""
from sqlalchemy import select

from app.extensions import db
from app.models import Attendance, Call, TicketStatus, TicketStatusHistory, UserRole
from tests.conftest import login


def call(client, h):
    response = client.post("/api/attendant/call-next", headers=h)
    assert response.status_code == 200, response.json
    return response.json


def post(client, h, ticket_id, action):
    return client.post(f"/api/attendant/tickets/{ticket_id}/{action}", headers=h)


def test_start_and_finish(client, attendant, issue, clock, app):
    issue("SP")
    h = attendant["headers"]
    ticket_id = call(client, h)["ticket"]["id"]
    clock.advance(minutes=1)
    started = post(client, h, ticket_id, "start")
    assert started.status_code == 200
    assert started.json["ticket"]["status"] == "EM_ATENDIMENTO"
    clock.advance(minutes=4, seconds=30)
    finished = post(client, h, ticket_id, "finish")
    assert finished.status_code == 200
    assert finished.json["ticket"]["status"] == "ATENDIDA"
    assert finished.json["attendance"]["duration_seconds"] == 270
    assert finished.json["attendance"]["result"] == "CONCLUIDO"

    with app.app_context():
        att = db.session.scalar(select(Attendance))
        assert att.user_id == attendant["user"]["id"] and att.counter_id == attendant["counter_id"]
        history = db.session.scalars(select(TicketStatusHistory).where(TicketStatusHistory.ticket_id == ticket_id).order_by(TicketStatusHistory.id)).all()
        assert [h.to_status.value for h in history] == ["EMITIDA", "AGUARDANDO", "CHAMADA", "EM_ATENDIMENTO", "ATENDIDA"]
        assert all(h.user_id == attendant["user"]["id"] for h in history[2:])


def test_cannot_finish_before_start(client, attendant, issue):
    issue("SG")
    ticket_id = call(client, attendant["headers"])["ticket"]["id"]
    response = post(client, attendant["headers"], ticket_id, "finish")
    assert response.status_code == 422
    assert response.json["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_recall_creates_new_call_record(client, attendant, issue, app):
    issue("SE")
    h = attendant["headers"]
    ticket_id = call(client, h)["ticket"]["id"]
    response = post(client, h, ticket_id, "recall")
    assert response.status_code == 200
    assert response.json["attempt_number"] == 2
    assert response.json["is_repeat"] is True
    assert response.json["ticket"]["status"] == "CHAMADA_NOVAMENTE"
    assert response.json["announcement"]["text"].startswith("Última chamada, senha de retirada de exames SE001")
    with app.app_context():
        calls = db.session.scalars(select(Call).order_by(Call.id)).all()
        assert [c.attempt_number for c in calls] == [1, 2]  # histórico preservado


def test_third_call_is_not_allowed(client, attendant, issue):
    issue("SG")
    h = attendant["headers"]
    ticket_id = call(client, h)["ticket"]["id"]
    assert post(client, h, ticket_id, "recall").status_code == 200
    response = post(client, h, ticket_id, "recall")
    assert response.status_code == 422
    assert response.json["error"]["code"] in {"MAX_CALLS_REACHED", "INVALID_STATUS_TRANSITION"}


def test_no_show_after_two_calls_releases_queue(client, attendant, issue):
    issue("SG")
    issue("SG")
    h = attendant["headers"]
    ticket_id = call(client, h)["ticket"]["id"]
    early = post(client, h, ticket_id, "no-show")
    assert early.status_code == 422 and early.json["error"]["code"] == "SECOND_CALL_REQUIRED"
    assert post(client, h, ticket_id, "recall").status_code == 200
    response = post(client, h, ticket_id, "no-show")
    assert response.status_code == 200
    assert response.json["ticket"]["status"] == "NAO_COMPARECEU"
    # fila liberada: o guichê pode chamar a próxima
    assert call(client, h)["ticket"]["short_code"] == "SG002"


def test_client_shows_up_after_recall(client, attendant, issue):
    issue("SP")
    h = attendant["headers"]
    ticket_id = call(client, h)["ticket"]["id"]
    post(client, h, ticket_id, "recall")
    assert post(client, h, ticket_id, "start").json["ticket"]["status"] == "EM_ATENDIMENTO"


def test_other_counter_cannot_operate_ticket(client, attendant, issue, make_user, make_counter):
    issue("SP")
    ticket_id = call(client, attendant["headers"])["ticket"]["id"]
    other_counter = make_counter()
    other = login(client, make_user(UserRole.ATTENDANT, [other_counter]))
    client.post("/api/attendant/session", json={"counter_id": other_counter}, headers=other)
    for action in ("start", "recall", "finish", "no-show"):
        response = post(client, other, ticket_id, action)
        assert response.status_code == 403
        assert response.json["error"]["code"] == "TICKET_NOT_OWNED"


def test_state_endpoint_reports_current_ticket(client, attendant, issue):
    issue("SE")
    h = attendant["headers"]
    ticket_id = call(client, h)["ticket"]["id"]
    state = client.get("/api/attendant/state", headers=h).json
    assert state["session"]["counter"]["id"] == attendant["counter_id"]
    assert state["current"]["ticket"]["id"] == ticket_id
    assert state["current"]["attempt_number"] == 1


def test_counter_session_rules(client, make_user, make_counter):
    c1, c2, c3 = make_counter(), make_counter(), make_counter()
    a = login(client, make_user(UserRole.ATTENDANT, [c1, c2]))
    b = login(client, make_user(UserRole.ATTENDANT, [c1]))
    assert client.post("/api/attendant/session", json={"counter_id": c3}, headers=a).status_code == 403
    assert client.post("/api/attendant/session", json={"counter_id": c1}, headers=a).status_code == 201
    occupied = client.post("/api/attendant/session", json={"counter_id": c1}, headers=b)
    assert occupied.status_code == 409 and occupied.json["error"]["code"] == "COUNTER_OCCUPIED"
    # troca de guichê fecha a sessão anterior e libera o guichê 1
    assert client.post("/api/attendant/session", json={"counter_id": c2}, headers=a).status_code == 201
    assert client.post("/api/attendant/session", json={"counter_id": c1}, headers=b).status_code == 201
    assert client.delete("/api/attendant/session", headers=b).status_code == 204


def test_cannot_leave_counter_with_active_ticket(client, attendant, issue):
    issue("SG")
    call(client, attendant["headers"])
    response = client.delete("/api/attendant/session", headers=attendant["headers"])
    assert response.status_code == 409


def test_ticket_detail_contains_history(client, attendant, issue, admin_headers):
    issue("SP")
    ticket_id = call(client, attendant["headers"])["ticket"]["id"]
    post(client, attendant["headers"], ticket_id, "recall")
    detail = client.get(f"/api/tickets/{ticket_id}", headers=admin_headers).json
    assert [c["attempt_number"] for c in detail["calls"]] == [1, 2]
    assert detail["status"] == TicketStatus.CHAMADA_NOVAMENTE.value
    assert len(detail["status_history"]) == 4
