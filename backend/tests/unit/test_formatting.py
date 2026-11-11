from datetime import date, datetime

import pytest

from app.models import Ticket, TicketType
from app.services.announcement import build_announcement
from app.services.business_hours import BusinessHours
from app.services.ticket_service import format_ticket_code
from tests.conftest import RECIFE


def test_ticket_code_pattern():
    assert format_ticket_code(date(2026, 11, 10), TicketType.SP, 1) == "261110-SP001"
    assert format_ticket_code(date(2027, 1, 5), TicketType.SG, 42) == "270105-SG042"
    assert format_ticket_code(date(2026, 12, 31), TicketType.SE, 999) == "261231-SE999"


def test_announcement_texts():
    ticket = Ticket(code="261110-SP001", type=TicketType.SP)
    first = build_announcement(ticket, 2, repeat=False)
    assert first["text"] == "Senha prioritária SP001, dirigir-se ao guichê 02."
    again = build_announcement(ticket, 2, repeat=True)
    assert again["text"] == "Última chamada, senha prioritária SP001, guichê 02."
    assert "S P 0 0 1" in first["speech"]


@pytest.mark.parametrize(
    "hhmm, calling, issuing",
    [("05:59", False, False), ("06:00", False, True), ("06:59", False, True), ("07:00", True, True),
     ("12:00", True, True), ("16:59", True, True), ("17:00", False, False), ("23:00", False, False)],
)
def test_business_hours(app, hhmm, calling, issuing):
    at = datetime.strptime(f"2026-11-10 {hhmm}", "%Y-%m-%d %H:%M").replace(tzinfo=RECIFE)
    with app.app_context():
        assert BusinessHours.is_calling_allowed(at) is calling
        assert BusinessHours.is_issuing_allowed(at) is issuing


def test_business_hours_can_be_disabled(app):
    at = datetime(2026, 11, 10, 22, 0, tzinfo=RECIFE)
    with app.app_context():
        app.config["ENFORCE_BUSINESS_HOURS"] = False
        try:
            assert BusinessHours.is_calling_allowed(at)
        finally:
            app.config["ENFORCE_BUSINESS_HOURS"] = True
