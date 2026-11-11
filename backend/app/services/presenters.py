"""Conversão de entidades para payloads JSON (respostas e eventos)."""
from __future__ import annotations

from typing import Any

from app.models import Call, Ticket
from app.schemas.counter import CounterOut
from app.schemas.ticket import TicketOut
from app.services.announcement import build_announcement
from app.schemas.common import serialize_local


def ticket_payload(ticket: Ticket) -> dict[str, Any]:
    return TicketOut.model_validate(ticket).model_dump(mode="json")


def call_payload(ticket: Ticket, call: Call) -> dict[str, Any]:
    repeat = call.attempt_number > 1
    return {
        "ticket": ticket_payload(ticket),
        "counter": CounterOut.model_validate(call.counter).model_dump(mode="json"),
        "attempt_number": call.attempt_number,
        "is_repeat": repeat,
        "called_at": serialize_local(call.called_at),
        "announcement": build_announcement(ticket, call.counter.number, repeat=repeat),
    }
