from __future__ import annotations

import datetime as dt
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import TicketStatus, TicketType
from app.schemas.common import PaginationQuery, PeriodQuery


class ReportQuery(PeriodQuery):
    model_config = ConfigDict(extra="ignore")

    type: TicketType | None = None


class DailyReportQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    day: dt.date | None = Field(None, alias="date")
    type: TicketType | None = None


class MonthlyReportQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    month: str | None = Field(None, description="Formato YYYY-MM", pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    type: TicketType | None = None


class HistoryQuery(ReportQuery, PaginationQuery):
    model_config = ConfigDict(extra="ignore")

    status: TicketStatus | None = None


class AuditQuery(PeriodQuery, PaginationQuery):
    model_config = ConfigDict(extra="ignore")

    user_id: int | None = None
    action: str | None = Field(None, max_length=60)
    entity: str | None = Field(None, max_length=60)

    @field_validator("action", "entity")
    @classmethod
    def _upper(cls, v: str | None) -> str | None:
        return v.strip() if v else v
