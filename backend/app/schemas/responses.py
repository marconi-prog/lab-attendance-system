"""Schemas das respostas que os controllers montam como dicionário.

Servem à documentação OpenAPI e são verificados pelo teste de contrato
(tests/integration/test_openapi.py), que valida respostas reais contra eles.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from pydantic import BaseModel, Field

from app.models import TicketStatus, TicketType
from app.schemas.attendance import CurrentTicketOut
from app.schemas.common import PageMeta
from app.schemas.counter import CounterOut, CounterSessionOut
from app.schemas.ticket import AttendanceOut, TicketOut
from app.schemas.user import CounterBrief, UserBrief, UserOut


# ------------------------------------------------------------------ comuns
class HealthOut(BaseModel):
    status: str = Field(examples=["ok"])
    database: str = Field(examples=["ok"])
    version: str
    time: dt.datetime


class BusinessHoursOut(BaseModel):
    open: str = Field(examples=["07:00"])
    close: str = Field(examples=["17:00"])
    issue_open: str = Field(examples=["06:00"])
    enforced: bool
    timezone: str = Field(examples=["America/Recife"])
    calling_allowed_now: bool
    issuing_allowed_now: bool


class AnnouncementOut(BaseModel):
    text: str = Field(examples=["Senha prioritária SP001, dirigir-se ao guichê 02."])
    speech: str = Field(examples=["Senha prioritária S P 0 0 1, dirigir-se ao guichê 02."])


class PanelItemOut(BaseModel):
    call_id: int
    ticket_id: int
    code: str = Field(examples=["261110-SP001"])
    short_code: str = Field(examples=["SP001"])
    type: TicketType
    type_label: str
    counter_number: int
    counter_label: str = Field(examples=["02"])
    counter_name: str
    attempt_number: int
    is_repeat: bool
    called_at: dt.datetime
    announcement: AnnouncementOut


class WaitingTicketOut(BaseModel):
    ticket_id: int
    short_code: str = Field(examples=["SG004"])
    position: int = Field(description="Posição na fila da categoria (1 = próxima)")
    issued_at: dt.datetime


class WaitingQueueOut(BaseModel):
    type: TicketType
    label: str
    total: int = Field(description="Total aguardando na fila (a lista traz no máximo 8)")
    tickets: list[WaitingTicketOut]


class NextUpOut(BaseModel):
    ticket_id: int
    short_code: str
    type: TicketType


class InServiceOut(BaseModel):
    ticket_id: int
    short_code: str
    type: TicketType
    counter_label: str = Field(examples=["02"])


class PanelSnapshotOut(BaseModel):
    lab_name: str
    server_time: dt.datetime
    latest: list[PanelItemOut] = Field(description="Até 5 senhas chamadas, da mais recente para a mais antiga")
    total_waiting: int
    queues: list[WaitingQueueOut] = Field(description="Senhas aguardando por fila (SP, SE, SG), em ordem de atendimento")
    next_up: list[NextUpOut] = Field(description="Previsão das próximas chamadas pelo ciclo de prioridade")
    in_service: list[InServiceOut] = Field(description="Senhas em atendimento agora")


# ------------------------------------------------------------------- senhas
class TicketTypeInfo(BaseModel):
    type: TicketType
    label: str


class TicketTypesOut(BaseModel):
    types: list[TicketTypeInfo]
    issuing_allowed: bool
    business_hours: BusinessHoursOut


class TicketPageOut(BaseModel):
    items: list[TicketOut]
    meta: PageMeta


# -------------------------------------------------------------- atendimento
class QueueSummaryOut(BaseModel):
    waiting: dict[str, int] = Field(description="Senhas aguardando por categoria", examples=[{"SP": 2, "SE": 1, "SG": 4}])
    total_waiting: int
    next_type: TicketType | None = Field(description="Categoria que será chamada pelo ciclo de prioridade")
    last_called_type: TicketType | None
    calling_allowed: bool


class AttendantStateOut(BaseModel):
    user: UserBrief
    session: CounterSessionOut | None
    current: CurrentTicketOut | None
    queue: QueueSummaryOut


class AvailableCounterOut(BaseModel):
    counter: CounterOut
    occupied_by: UserBrief | None


class AvailableCountersOut(BaseModel):
    items: list[AvailableCounterOut]


class CallResultOut(BaseModel):
    ticket: TicketOut
    counter: CounterOut
    attempt_number: int = Field(description="1 = primeira chamada, 2 = última chamada")
    is_repeat: bool
    called_at: dt.datetime
    announcement: AnnouncementOut


class AttendanceResultOut(BaseModel):
    ticket: TicketOut
    attendance: AttendanceOut


class TicketResultOut(BaseModel):
    ticket: TicketOut


# ------------------------------------------------------------------- gestão
class UserPageOut(BaseModel):
    items: list[UserOut]
    meta: PageMeta


class CounterListOut(BaseModel):
    items: list[CounterOut]


class CounterSessionListOut(BaseModel):
    items: list[CounterSessionOut]


class AuditLogOut(BaseModel):
    id: int
    user: UserBrief | None
    action: str = Field(examples=["TICKET_CALLED"])
    entity: str = Field(examples=["ticket"])
    entity_id: str | None
    details: dict[str, Any] | None
    ip_address: str | None
    created_at: dt.datetime


class AuditPageOut(BaseModel):
    items: list[AuditLogOut]
    meta: PageMeta


class CloseDayOut(BaseModel):
    discarded: int = Field(description="Senhas AGUARDANDO que foram descartadas")


# ---------------------------------------------------------------- relatórios
class PeriodOut(BaseModel):
    start_date: dt.date
    end_date: dt.date


class TotalsOut(BaseModel):
    issued: int
    attended: int
    no_show: int
    discarded: int
    pending: int
    not_attended: int = Field(description="no_show + discarded")
    avg_attendance_seconds: float | None
    avg_wait_seconds: float | None = Field(description="Média entre emissão e primeira chamada")


class TypeStatsOut(TotalsOut):
    type: TicketType
    label: str


class AttendantStatsOut(BaseModel):
    user_id: int
    name: str
    attended: int
    avg_attendance_seconds: float | None


class CounterStatsOut(BaseModel):
    counter_id: int
    number: int
    name: str
    attended: int
    avg_attendance_seconds: float | None


class SummaryReportOut(BaseModel):
    period: PeriodOut
    type: TicketType | None
    totals: TotalsOut
    by_type: list[TypeStatsOut]
    by_status: dict[TicketStatus, int]
    by_attendant: list[AttendantStatsOut]
    by_counter: list[CounterStatsOut]


class HourStatOut(BaseModel):
    hour: int
    issued: int


class DailyReportOut(SummaryReportOut):
    date: dt.date
    by_hour: list[HourStatOut]


class DayStatOut(BaseModel):
    date: dt.date
    issued: int
    attended: int
    not_attended: int
    avg_attendance_seconds: float | None


class MonthlyReportOut(SummaryReportOut):
    month: str = Field(examples=["2026-11"])
    by_day: list[DayStatOut]


class HistoryRowOut(BaseModel):
    ticket_id: int
    code: str
    type: TicketType
    type_label: str
    status: TicketStatus
    issued_at: dt.datetime
    first_called_at: dt.datetime | None
    last_called_at: dt.datetime | None
    call_count: int
    started_at: dt.datetime | None
    finished_at: dt.datetime | None
    duration_seconds: int | None
    attendant: UserBrief | None
    counter: CounterBrief | None


class HistoryPageOut(BaseModel):
    items: list[HistoryRowOut]
    meta: PageMeta


# ---------------------------------------------------------------- dashboard
class CurrentTicketBrief(BaseModel):
    id: int
    code: str
    status: TicketStatus


class OpenSessionInfoOut(BaseModel):
    session_id: int
    counter: CounterBrief
    attendant: UserBrief
    opened_at: dt.datetime
    current_ticket: CurrentTicketBrief | None


class DashboardOut(BaseModel):
    date: dt.date
    issued: int
    attended: int
    waiting: int
    in_progress: int
    no_show: int
    discarded: int
    by_status: dict[TicketStatus, int]
    avg_attendance_seconds: float | None
    avg_wait_seconds: float | None
    by_type: list[TypeStatsOut]
    queue: QueueSummaryOut
    open_sessions: list[OpenSessionInfoOut]
    recent_calls: list[PanelItemOut]
    business_hours: BusinessHoursOut


class DatabaseInfoOut(BaseModel):
    engine: str
    version: str


class SystemInfoOut(BaseModel):
    app_name: str
    version: str
    lab_name: str
    environment: str
    server_time: dt.datetime
    database: DatabaseInfoOut
    business_hours: BusinessHoursOut
    counts: dict[str, int]
