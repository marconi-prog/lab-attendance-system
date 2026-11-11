from __future__ import annotations

from pydantic import ConfigDict, Field

from app.schemas.common import LocalDateTime, OutModel, StrictModel
from app.schemas.ticket import AttendanceOut, TicketOut


class OpenSessionRequest(StrictModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"counter_id": 2}]})

    counter_id: int = Field(ge=1)


class CurrentTicketOut(OutModel):
    ticket: TicketOut
    attempt_number: int
    called_at: LocalDateTime
    attendance: AttendanceOut | None = None
