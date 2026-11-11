from __future__ import annotations

from flask_jwt_extended import current_user

from app.schemas.attendance import CurrentTicketOut, OpenSessionRequest
from app.schemas.counter import CounterOut, CounterSessionOut
from app.schemas.ticket import AttendanceOut, TicketOut
from app.schemas.user import UserBrief
from app.services.attendance_service import AttendanceService
from app.services.presenters import call_payload
from app.services.queue_service import QueueService


def _current_payload(session) -> dict | None:
    current = AttendanceService.current_ticket(session) if session else None
    if not current:
        return None
    ticket, call = current
    return CurrentTicketOut(
        ticket=TicketOut.model_validate(ticket),
        attempt_number=call.attempt_number,
        called_at=call.called_at,
        attendance=AttendanceOut.model_validate(ticket.attendance) if ticket.attendance else None,
    ).model_dump(mode="json")


def state():
    session = AttendanceService.current_session(current_user)
    return {
        "user": UserBrief.model_validate(current_user).model_dump(),
        "session": CounterSessionOut.model_validate(session).model_dump(mode="json") if session else None,
        "current": _current_payload(session),
        "queue": QueueService.summary(),
    }


def counters():
    return {
        "items": [
            {
                "counter": CounterOut.model_validate(counter).model_dump(mode="json"),
                "occupied_by": UserBrief.model_validate(occupied).model_dump() if occupied else None,
            }
            for counter, occupied in AttendanceService.available_counters(current_user)
        ]
    }


def open_session(body: OpenSessionRequest):
    session = AttendanceService.open_session(current_user, body.counter_id)
    return CounterSessionOut.model_validate(session), 201


def close_session():
    AttendanceService.close_session(current_user)
    return None


def call_next():
    session = AttendanceService.require_session(current_user)
    ticket, call = QueueService.call_next(user_id=current_user.id, session=session)
    return call_payload(ticket, call)


def recall(ticket_id: int):
    session = AttendanceService.require_session(current_user)
    ticket, call = QueueService.recall(user_id=current_user.id, session=session, ticket_id=ticket_id)
    return call_payload(ticket, call)


def start(ticket_id: int):
    session = AttendanceService.require_session(current_user)
    attendance = AttendanceService.start(user=current_user, session=session, ticket_id=ticket_id)
    return {"ticket": TicketOut.model_validate(attendance.ticket).model_dump(mode="json"),
            "attendance": AttendanceOut.model_validate(attendance).model_dump(mode="json")}


def finish(ticket_id: int):
    session = AttendanceService.require_session(current_user)
    attendance = AttendanceService.finish(user=current_user, session=session, ticket_id=ticket_id)
    return {"ticket": TicketOut.model_validate(attendance.ticket).model_dump(mode="json"),
            "attendance": AttendanceOut.model_validate(attendance).model_dump(mode="json")}


def no_show(ticket_id: int):
    session = AttendanceService.require_session(current_user)
    ticket = AttendanceService.no_show(user=current_user, session=session, ticket_id=ticket_id)
    return {"ticket": TicketOut.model_validate(ticket).model_dump(mode="json")}
