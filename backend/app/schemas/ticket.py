from __future__ import annotations

import datetime as dt
from datetime import date

from pydantic import ConfigDict, Field, computed_field

from app.models import AttendanceResult, TicketStatus, TicketType
from app.models.enums import TICKET_TYPE_LABELS
from app.schemas.common import LocalDateTime, OutModel, PaginationQuery, StrictModel
from app.schemas.counter import CounterOut
from app.schemas.user import UserBrief
from app.services.state_machine import STATUS_LABELS


class TicketCreate(StrictModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"type": "SP"}]})

    type: TicketType


class TicketOut(OutModel):
    id: int
    code: str
    short_code: str
    type: TicketType
    status: TicketStatus
    daily_sequence: int
    reference_date: date
    issued_at: LocalDateTime
    updated_at: LocalDateTime

    @computed_field
    @property
    def type_label(self) -> str:
        return TICKET_TYPE_LABELS[self.type]

    @computed_field
    @property
    def status_label(self) -> str:
        return STATUS_LABELS[self.status]


class CallOut(OutModel):
    id: int
    attempt_number: int
    called_at: LocalDateTime
    counter: CounterOut
    user: UserBrief


class AttendanceOut(OutModel):
    id: int
    started_at: LocalDateTime
    finished_at: LocalDateTime | None = None
    duration_seconds: int | None = None
    result: AttendanceResult
    user: UserBrief


class StatusHistoryOut(OutModel):
    id: int
    from_status: TicketStatus | None = None
    to_status: TicketStatus
    user_id: int | None = None
    counter_id: int | None = None
    created_at: LocalDateTime


class TicketDetailOut(TicketOut):
    calls: list[CallOut] = []
    attendance: AttendanceOut | None = None
    status_history: list[StatusHistoryOut] = []


class TicketListQuery(PaginationQuery):
    model_config = ConfigDict(extra="ignore")

    day: dt.date | None = Field(None, alias="date")
    status: TicketStatus | None = None
    type: TicketType | None = None


class IssuedTicketOut(OutModel):
    ticket: TicketOut
    waiting_ahead: int = Field(description="Senhas da mesma categoria aguardando antes desta")
