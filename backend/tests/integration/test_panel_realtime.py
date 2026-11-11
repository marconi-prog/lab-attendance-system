"""Painel público e eventos Socket.IO."""
from app.extensions import socketio
from app.models import UserRole
from tests.conftest import PASSWORD, login


def call(client, h):
    return client.post("/api/attendant/call-next", headers=h).json


def test_panel_shows_only_called_tickets(client, attendant, issue):
    issue("SP")
    issue("SG")
    assert client.get("/api/panel").json["latest"] == []  # emitidas, mas não chamadas
    call(client, attendant["headers"])
    latest = client.get("/api/panel").json["latest"]
    assert [item["short_code"] for item in latest] == ["SP001"]
    assert latest[0]["counter_number"] is not None


def test_panel_keeps_last_five_and_moves_recall_to_top(client, attendant, issue):
    h = attendant["headers"]
    for _ in range(7):
        issue("SG")
    ids = []
    for _ in range(6):
        ticket = call(client, h)["ticket"]
        ids.append(ticket["id"])
        client.post(f"/api/attendant/tickets/{ticket['id']}/start", headers=h)
        client.post(f"/api/attendant/tickets/{ticket['id']}/finish", headers=h)
    latest = client.get("/api/panel").json["latest"]
    assert [i["short_code"] for i in latest] == ["SG006", "SG005", "SG004", "SG003", "SG002"]
    ticket = call(client, h)["ticket"]
    client.post(f"/api/attendant/tickets/{ticket['id']}/recall", headers=h)
    latest = client.get("/api/panel").json["latest"]
    assert latest[0]["short_code"] == "SG007" and latest[0]["is_repeat"] is True
    assert len(latest) == 5 and len({i["ticket_id"] for i in latest}) == 5


def test_panel_socket_receives_call_events(app, client, attendant, issue):
    panel = socketio.test_client(app, namespace="/panel")
    assert panel.is_connected("/panel")
    initial = panel.get_received("/panel")
    assert initial[0]["name"] == "panel:updated"

    issue("SP")
    call(client, attendant["headers"])
    events = {e["name"]: e["args"][0] for e in panel.get_received("/panel")}
    assert "ticket:issued" not in events  # o painel não recebe emissões
    assert events["ticket:called"]["announcement"]["text"].startswith("Senha prioritária SP001")
    assert events["panel:updated"]["latest"][0]["short_code"] == "SP001"
    panel.disconnect(namespace="/panel")


def test_panel_recall_event(app, client, attendant, issue):
    issue("SG")
    ticket_id = call(client, attendant["headers"])["ticket"]["id"]
    panel = socketio.test_client(app, namespace="/panel")
    panel.get_received("/panel")
    client.post(f"/api/attendant/tickets/{ticket_id}/recall", headers=attendant["headers"])
    names = [e["name"] for e in panel.get_received("/panel")]
    assert "ticket:recalled" in names
    panel.disconnect(namespace="/panel")


def test_staff_namespace_requires_valid_token(app, client, make_user):
    anonymous = socketio.test_client(app, namespace="/staff")
    assert not anonymous.is_connected("/staff")
    bad = socketio.test_client(app, namespace="/staff", auth={"token": "invalid"})
    assert not bad.is_connected("/staff")

    user = make_user(UserRole.ADMIN)
    token = client.post("/api/auth/login", json={"email": user["email"], "password": PASSWORD}).json["access_token"]
    staff = socketio.test_client(app, namespace="/staff", auth={"token": token})
    assert staff.is_connected("/staff")
    client.post("/api/tickets", json={"type": "SE"})
    names = [e["name"] for e in staff.get_received("/staff")]
    assert "ticket:issued" in names and "queue:updated" in names
    staff.disconnect(namespace="/staff")


def test_staff_namespace_rejects_revoked_token(app, client, make_user):
    user = make_user()
    headers = login(client, user)
    token = headers["Authorization"].split()[1]
    client.post("/api/auth/logout", json={}, headers=headers)
    staff = socketio.test_client(app, namespace="/staff", auth={"token": token})
    assert not staff.is_connected("/staff")


# ------------------------------------------------- quadro "aguardando" (fila)
def _queue(snapshot, ticket_type):
    return next(q for q in snapshot["queues"] if q["type"] == ticket_type)


def test_panel_board_shows_waiting_tickets_by_queue(client, issue):
    for t in ["SG", "SP", "SE", "SG", "SP"]:
        issue(t)
    snap = client.get("/api/panel").json
    assert snap["total_waiting"] == 5
    assert [t["short_code"] for t in _queue(snap, "SP")["tickets"]] == ["SP001", "SP002"]
    assert [t["short_code"] for t in _queue(snap, "SG")["tickets"]] == ["SG001", "SG002"]
    assert [t["position"] for t in _queue(snap, "SG")["tickets"]] == [1, 2]
    assert _queue(snap, "SE")["total"] == 1
    # previsão segue o ciclo SP → SE → SP → SG → SG
    assert [n["short_code"] for n in snap["next_up"]] == ["SP001", "SE001", "SP002", "SG001", "SG002"]
    assert snap["latest"] == []  # nada chamado ainda


def test_panel_board_moves_ticket_from_waiting_to_called_and_in_service(client, attendant, issue):
    issue("SP")
    issue("SG")
    h = attendant["headers"]
    ticket = call(client, h)["ticket"]
    snap = client.get("/api/panel").json
    assert _queue(snap, "SP")["total"] == 0  # saiu da fila
    assert snap["latest"][0]["short_code"] == "SP001"  # foi para "chamadas"
    assert [n["short_code"] for n in snap["next_up"]] == ["SG001"]  # previsão continua após o SP
    client.post(f"/api/attendant/tickets/{ticket['id']}/start", headers=h)
    snap = client.get("/api/panel").json
    assert snap["in_service"][0]["short_code"] == "SP001"
    client.post(f"/api/attendant/tickets/{ticket['id']}/finish", headers=h)
    assert client.get("/api/panel").json["in_service"] == []


def test_panel_queue_preview_is_limited_but_total_is_exact(client, issue):
    for _ in range(11):
        issue("SG")
    queue = _queue(client.get("/api/panel").json, "SG")
    assert queue["total"] == 11 and len(queue["tickets"]) == 8


def test_panel_socket_updates_on_issuance(app, client):
    panel = socketio.test_client(app, namespace="/panel")
    panel.get_received("/panel")
    client.post("/api/tickets", json={"type": "SE"})
    updates = [e["args"][0] for e in panel.get_received("/panel") if e["name"] == "panel:updated"]
    assert updates and _queue(updates[-1], "SE")["tickets"][0]["short_code"] == "SE001"
    panel.disconnect(namespace="/panel")
