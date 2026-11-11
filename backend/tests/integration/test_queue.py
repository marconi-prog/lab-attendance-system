"""Chamada de senhas: ciclo de prioridade, atomicidade e expediente."""
import threading

from sqlalchemy import func, select

from app.extensions import db
from app.models import Call, Ticket, TicketStatus, UserRole
from tests.conftest import login


def call_next(client, headers):
    return client.post("/api/attendant/call-next", headers=headers)


def serve(client, headers, ticket_id):
    assert client.post(f"/api/attendant/tickets/{ticket_id}/start", headers=headers).status_code == 200
    assert client.post(f"/api/attendant/tickets/{ticket_id}/finish", headers=headers).status_code == 200


def drain(client, headers) -> list[str]:
    order = []
    while (response := call_next(client, headers)).status_code == 200:
        order.append(response.json["ticket"]["short_code"])
        serve(client, headers, response.json["ticket"]["id"])
    assert response.json["error"]["code"] == "QUEUE_EMPTY"
    return order


def test_priority_cycle(client, attendant, issue):
    for t in ["SG", "SG", "SE", "SP", "SP", "SP", "SE", "SG"]:
        issue(t)
    order = drain(client, attendant["headers"])
    assert order == ["SP001", "SE001", "SP002", "SE002", "SP003", "SG001", "SG002", "SG003"]


def test_cycle_handles_empty_categories(client, attendant, issue):
    issue("SG")
    issue("SG")
    assert drain(client, attendant["headers"]) == ["SG001", "SG002"]
    issue("SP")
    issue("SP")
    assert drain(client, attendant["headers"]) == ["SP001", "SP002"]


def test_new_priority_ticket_interleaves(client, attendant, issue):
    issue("SG")
    issue("SG")
    h = attendant["headers"]
    first = call_next(client, h).json["ticket"]
    serve(client, h, first["id"])
    issue("SP")  # chega uma prioritária depois de uma SG
    assert call_next(client, h).json["ticket"]["short_code"] == "SP001"


def test_empty_queue(client, attendant):
    response = call_next(client, attendant["headers"])
    assert response.status_code == 422
    assert response.json["error"]["code"] == "QUEUE_EMPTY"


def test_counter_cannot_call_while_busy(client, attendant, issue):
    issue("SG")
    issue("SG")
    assert call_next(client, attendant["headers"]).status_code == 200
    response = call_next(client, attendant["headers"])
    assert response.status_code == 409
    assert response.json["error"]["code"] == "COUNTER_BUSY"


def test_call_requires_counter_session(client, make_user, make_counter, issue):
    issue("SP")
    headers = login(client, make_user(UserRole.ATTENDANT, [make_counter()]))
    response = call_next(client, headers)
    assert response.status_code == 422
    assert response.json["error"]["code"] == "NO_COUNTER_SESSION"


def test_calls_blocked_outside_business_hours(client, attendant, issue, clock):
    issue("SP")
    clock.set("2026-11-10 17:00")
    response = call_next(client, attendant["headers"])
    assert response.status_code == 422
    assert response.json["error"]["code"] == "OUTSIDE_BUSINESS_HOURS"
    clock.set("2026-11-11 06:59")
    assert call_next(client, attendant["headers"]).status_code == 422


def test_in_progress_attendance_can_finish_after_closing(client, attendant, issue, clock):
    issue("SE")
    clock.set("2026-11-10 16:58")
    ticket = call_next(client, attendant["headers"]).json["ticket"]
    client.post(f"/api/attendant/tickets/{ticket['id']}/start", headers=attendant["headers"])
    clock.set("2026-11-10 17:20")
    response = client.post(f"/api/attendant/tickets/{ticket['id']}/finish", headers=attendant["headers"])
    assert response.status_code == 200
    assert response.json["attendance"]["duration_seconds"] == 22 * 60


def test_day_closing_discards_only_waiting(client, attendant, issue, admin_headers, app, clock):
    for t in ["SP", "SG", "SG", "SE"]:
        issue(t)
    called = call_next(client, attendant["headers"]).json["ticket"]
    clock.set("2026-11-10 17:00")
    response = client.post("/api/admin/close-day", headers=admin_headers)
    assert response.status_code == 200 and response.json["discarded"] == 3
    with app.app_context():
        statuses = dict(db.session.execute(select(Ticket.code, Ticket.status)).all())
    assert statuses[called["code"]] == TicketStatus.CHAMADA
    assert sorted(s.value for c, s in statuses.items() if c != called["code"]) == ["DESCARTADA"] * 3


def test_scheduled_closing(app, issue, clock):
    from app.services.day_closing_service import DayClosingService

    issue("SG")
    clock.set("2026-11-10 17:01")
    with app.app_context():
        DayClosingService.run_scheduled()
        assert db.session.scalar(select(Ticket.status)) == TicketStatus.DESCARTADA
        db.session.remove()


def test_scheduled_closing_discards_previous_days(app, issue, clock):
    from app.services.day_closing_service import DayClosingService

    issue("SG")
    clock.set("2026-11-11 08:00")
    with app.app_context():
        DayClosingService.run_scheduled()
        assert db.session.scalar(select(Ticket.status)) == TicketStatus.DESCARTADA
        db.session.remove()


def test_concurrent_attendants_never_get_same_ticket(app, client, make_user, make_counter, issue):
    """10 guichês chamam ao mesmo tempo: cada um recebe uma senha distinta."""
    for t in ["SP"] * 4 + ["SE"] * 3 + ["SG"] * 3:
        issue(t)
    headers_list = []
    for _ in range(10):
        counter_id = make_counter()
        h = login(client, make_user(UserRole.ATTENDANT, [counter_id]))
        assert client.post("/api/attendant/session", json={"counter_id": counter_id}, headers=h).status_code == 201
        headers_list.append(h)

    barrier = threading.Barrier(len(headers_list))
    results = []
    lock = threading.Lock()

    def worker(h):
        c = app.test_client()
        barrier.wait()
        r = c.post("/api/attendant/call-next", headers=h)
        with lock:
            results.append((r.status_code, r.json))

    threads = [threading.Thread(target=worker, args=(h,)) for h in headers_list]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert [s for s, _ in results] == [200] * 10, results
    ids = [body["ticket"]["id"] for _, body in results]
    assert len(set(ids)) == 10
    with app.app_context():
        assert db.session.scalar(select(func.count(Call.id))) == 10
        assert db.session.scalar(select(func.count(Ticket.id)).where(Ticket.status == TicketStatus.CHAMADA)) == 10
    # Mesmo concorrente, a ordem global respeita o ciclo de prioridade.
    with app.app_context():
        order = [c.ticket.type.value for c in db.session.scalars(select(Call).order_by(Call.id))]
    assert order == ["SP", "SE", "SP", "SE", "SP", "SE", "SP", "SG", "SG", "SG"]


def test_concurrent_double_click_reserves_only_one(app, attendant, issue):
    for _ in range(5):
        issue("SG")
    barrier = threading.Barrier(5)
    statuses = []

    def worker():
        c = app.test_client()
        barrier.wait()
        statuses.append(c.post("/api/attendant/call-next", headers=attendant["headers"]).status_code)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert sorted(statuses) == [200, 409, 409, 409, 409]
