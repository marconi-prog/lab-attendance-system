from __future__ import annotations

from app.models import TicketType
from app.models.enums import TICKET_TYPE_LABELS
from app.schemas.ticket import IssuedTicketOut, TicketCreate, TicketDetailOut, TicketListQuery, TicketOut
from app.services.business_hours import BusinessHours
from app.services.ticket_service import TicketService
from app.utils.db import page_meta


def issue(body: TicketCreate):
    ticket, ahead = TicketService.issue(body.type)
    return IssuedTicketOut(ticket=TicketOut.model_validate(ticket), waiting_ahead=ahead), 201


def types():
    return {
        "types": [{"type": t.value, "label": TICKET_TYPE_LABELS[t]} for t in TicketType],
        "issuing_allowed": BusinessHours.is_issuing_allowed(),
        "business_hours": BusinessHours.describe(),
    }


def list_tickets(query: TicketListQuery):
    items, total = TicketService.list(query)
    return {
        "items": [TicketOut.model_validate(t).model_dump(mode="json") for t in items],
        "meta": page_meta(query.page, query.per_page, total),
    }


def get_ticket(ticket_id: int):
    return TicketDetailOut.model_validate(TicketService.get_detail(ticket_id))
