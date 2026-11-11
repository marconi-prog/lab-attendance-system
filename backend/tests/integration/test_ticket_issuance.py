"""Emissão de senhas: formato, sequência diária, concorrência e limites."""
import re
import threading

from sqlalchemy import func, select, update

from app.extensions import db
from app.models import DailySequence, Ticket, TicketStatus, TicketStatusHistory, TicketType


def test_issue_returns_code_in_expected_pattern(client):
    response = client.post("/api/tickets", json={"type": "SP"})
    assert response.status_code == 201
    ticket = response.json["ticket"]
    assert ticket["code"] == "261110-SP001"
    assert re.fullmatch(r"\d{6}-(SP|SE|SG)\d{3}", ticket["code"])
    assert ticket["status"] == "AGUARDANDO"
    assert ticket["short_code"] == "SP001"
    assert response.json["waiting_ahead"] == 0


def test_issue_records_emitida_then_aguardando(client, app):
    ticket_id = client.post("/api/tickets", json={"type": "SG"}).json["ticket"]["id"]
    with app.app_context():
        history = db.session.scalars(
            select(TicketStatusHistory).where(TicketStatusHistory.ticket_id == ticket_id).order_by(TicketStatusHistory.id)
        ).all()
        assert [(h.from_status, h.to_status) for h in history] == [
            (None, TicketStatus.EMITIDA),
            (TicketStatus.EMITIDA, TicketStatus.AGUARDANDO),
        ]


def test_sequence_is_independent_per_category(issue):
    codes = [issue(t)["code"] for t in ["SP", "SP", "SE", "SG", "SP", "SE"]]
    assert codes == ["261110-SP001", "261110-SP002", "261110-SE001", "261110-SG001", "261110-SP003", "261110-SE002"]


def test_sequence_restarts_every_day(issue, clock):
    assert issue("SG")["code"] == "261110-SG001"
    assert issue("SG")["code"] == "261110-SG002"
    clock.set("2026-11-11 08:00")
    assert issue("SG")["code"] == "261111-SG001"


def test_invalid_type_is_rejected(client):
    response = client.post("/api/tickets", json={"type": "XX"})
    assert response.status_code == 422
    assert response.json["error"]["code"] == "VALIDATION_ERROR"


def test_unknown_fields_are_rejected(client):
    assert client.post("/api/tickets", json={"type": "SP", "status": "ATENDIDA"}).status_code == 422


def test_non_json_body_is_rejected(client):
    assert client.post("/api/tickets", data="type=SP").status_code == 422


def test_issue_blocked_after_closing_time(client, clock):
    clock.set("2026-11-10 17:00")
    response = client.post("/api/tickets", json={"type": "SP"})
    assert response.status_code == 422
    assert response.json["error"]["code"] == "OUTSIDE_BUSINESS_HOURS"


def test_daily_limit(client, app, issue):
    issue("SE")
    with app.app_context():
        db.session.execute(update(DailySequence).values(last_sequence=999))
        db.session.commit()
    response = client.post("/api/tickets", json={"type": "SE"})
    assert response.status_code == 422
    assert response.json["error"]["code"] == "DAILY_LIMIT_REACHED"


def test_concurrent_issuance_never_duplicates_codes(app):
    """40 emissões simultâneas (mesma categoria e categorias diferentes)."""
    threads_per_type = {"SP": 20, "SG": 12, "SE": 8}
    barrier = threading.Barrier(sum(threads_per_type.values()))
    results: list[tuple[int, str]] = []
    lock = threading.Lock()

    def worker(ticket_type: str):
        local_client = app.test_client()
        barrier.wait()
        response = local_client.post("/api/tickets", json={"type": ticket_type})
        with lock:
            results.append((response.status_code, response.json["ticket"]["code"] if response.status_code == 201 else response.json))

    threads = [threading.Thread(target=worker, args=(t,)) for t, n in threads_per_type.items() for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert all(status == 201 for status, _ in results), results
    codes = [code for _, code in results]
    assert len(codes) == len(set(codes)) == 40
    for ticket_type, n in threads_per_type.items():
        expected = {f"261110-{ticket_type}{i:03d}" for i in range(1, n + 1)}
        assert {c for c in codes if ticket_type in c} == expected

    with app.app_context():
        assert db.session.scalar(select(func.count(Ticket.id))) == 40
        seqs = {s.ticket_type: s.last_sequence for s in db.session.scalars(select(DailySequence))}
        assert seqs == {TicketType.SP: 20, TicketType.SG: 12, TicketType.SE: 8}


def test_ticket_types_endpoint(client):
    body = client.get("/api/tickets/types").json
    assert [t["type"] for t in body["types"]] == ["SP", "SE", "SG"]
    assert body["issuing_allowed"] is True
