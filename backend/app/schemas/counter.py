from __future__ import annotations

from pydantic import ConfigDict, Field

from app.schemas.common import LocalDateTime, OutModel, StrictModel
from app.schemas.user import UserBrief


class CounterOut(OutModel):
    id: int
    name: str
    number: int
    active: bool
    created_at: LocalDateTime


class CounterCreate(StrictModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"name": "Guichê 06", "number": 6}]})

    name: str = Field(min_length=2, max_length=60)
    number: int = Field(ge=1, le=99)


class CounterUpdate(StrictModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"active": False}]})

    name: str | None = Field(None, min_length=2, max_length=60)
    number: int | None = Field(None, ge=1, le=99)
    active: bool | None = None


class CounterSessionOut(OutModel):
    id: int
    counter: CounterOut
    user: UserBrief
    opened_at: LocalDateTime
    closed_at: LocalDateTime | None = None


class CounterAvailabilityOut(OutModel):
    counter: CounterOut
    occupied_by: UserBrief | None = None
