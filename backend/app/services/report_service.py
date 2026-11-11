"""Relatórios — todos os números são agregados diretamente no MySQL.

O filtro de período usa tickets.reference_date (data local de emissão,
America/Recife), evitando conversões de fuso nas consultas.
"""
from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import and_, func, literal_column, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import Attendance, Call, Counter, Ticket, TicketStatus, TicketType, User
from app.models.enums import ACTIVE_STATUSES, TICKET_TYPE_LABELS
from app.schemas.common import serialize_local
from app.utils.clock import local_today, to_local
from app.utils.db import paginate

_PENDING = (TicketStatus.EMITIDA, TicketStatus.AGUARDANDO, *ACTIVE_STATUSES)


def _round(value) -> float | None:
    return round(float(value), 1) if value is not None else None


def _first_calls_subquery():
    return (
        select(Call.ticket_id.label("ticket_id"), func.min(Call.called_at).label("first_called_at"))
        .group_by(Call.ticket_id)
        .subquery()
    )


class ReportService:
    @staticmethod
    def _filters(start: date, end: date, ticket_type: TicketType | None) -> list:
        conditions = [Ticket.reference_date >= start, Ticket.reference_date <= end]
        if ticket_type:
            conditions.append(Ticket.type == ticket_type)
        return conditions

    @classmethod
    def summary(cls, start: date, end: date, ticket_type: TicketType | None = None) -> dict:
        conditions = cls._filters(start, end, ticket_type)

        status_rows = db.session.execute(
            select(Ticket.type, Ticket.status, func.count(Ticket.id)).where(*conditions).group_by(Ticket.type, Ticket.status)
        ).all()

        duration_rows = db.session.execute(
            select(Ticket.type, func.avg(Attendance.duration_seconds), func.count(Attendance.id))
            .join(Attendance, Attendance.ticket_id == Ticket.id)
            .where(*conditions, Attendance.finished_at.is_not(None))
            .group_by(Ticket.type)
        ).all()

        first_calls = _first_calls_subquery()
        wait_expr = func.timestampdiff(literal_column("SECOND"), Ticket.issued_at, first_calls.c.first_called_at)
        wait_rows = db.session.execute(
            select(Ticket.type, func.avg(wait_expr))
            .join(first_calls, first_calls.c.ticket_id == Ticket.id)
            .where(*conditions)
            .group_by(Ticket.type)
        ).all()

        overall_duration = db.session.execute(
            select(func.avg(Attendance.duration_seconds))
            .join(Ticket, Attendance.ticket_id == Ticket.id)
            .where(*conditions, Attendance.finished_at.is_not(None))
        ).scalar()
        overall_wait = db.session.execute(
            select(func.avg(wait_expr)).select_from(Ticket).join(first_calls, first_calls.c.ticket_id == Ticket.id).where(*conditions)
        ).scalar()

        per_type: dict[TicketType, dict] = {
            t: {"issued": 0, "attended": 0, "no_show": 0, "discarded": 0, "pending": 0} for t in TicketType
        }
        by_status = {s.value: 0 for s in TicketStatus}
        for t, status, count in status_rows:
            bucket = per_type[t]
            bucket["issued"] += count
            by_status[status.value] += count
            if status == TicketStatus.ATENDIDA:
                bucket["attended"] += count
            elif status == TicketStatus.NAO_COMPARECEU:
                bucket["no_show"] += count
            elif status == TicketStatus.DESCARTADA:
                bucket["discarded"] += count
            elif status in _PENDING:
                bucket["pending"] += count

        durations = {t: avg for t, avg, _ in duration_rows}
        waits = {t: avg for t, avg in wait_rows}
        types = [ticket_type] if ticket_type else list(TicketType)
        by_type = []
        for t in types:
            b = per_type[t]
            by_type.append(
                {
                    "type": t.value,
                    "label": TICKET_TYPE_LABELS[t],
                    **b,
                    "not_attended": b["no_show"] + b["discarded"],
                    "avg_attendance_seconds": _round(durations.get(t)),
                    "avg_wait_seconds": _round(waits.get(t)),
                }
            )

        totals = {key: sum(item[key] for item in by_type) for key in ("issued", "attended", "no_show", "discarded", "pending", "not_attended")}
        totals["avg_attendance_seconds"] = _round(overall_duration)
        totals["avg_wait_seconds"] = _round(overall_wait)

        return {
            "period": {"start_date": start.isoformat(), "end_date": end.isoformat()},
            "type": ticket_type.value if ticket_type else None,
            "totals": totals,
            "by_type": by_type,
            "by_status": by_status,
            "by_attendant": cls._by_attendant(conditions),
            "by_counter": cls._by_counter(conditions),
        }

    @staticmethod
    def _by_attendant(conditions: list) -> list[dict]:
        rows = db.session.execute(
            select(User.id, User.name, func.count(Attendance.id), func.avg(Attendance.duration_seconds))
            .join(Attendance, Attendance.user_id == User.id)
            .join(Ticket, Ticket.id == Attendance.ticket_id)
            .where(*conditions, Attendance.finished_at.is_not(None))
            .group_by(User.id, User.name)
            .order_by(func.count(Attendance.id).desc())
        ).all()
        return [{"user_id": r[0], "name": r[1], "attended": r[2], "avg_attendance_seconds": _round(r[3])} for r in rows]

    @staticmethod
    def _by_counter(conditions: list) -> list[dict]:
        rows = db.session.execute(
            select(Counter.id, Counter.number, Counter.name, func.count(Attendance.id), func.avg(Attendance.duration_seconds))
            .join(Attendance, Attendance.counter_id == Counter.id)
            .join(Ticket, Ticket.id == Attendance.ticket_id)
            .where(*conditions, Attendance.finished_at.is_not(None))
            .group_by(Counter.id, Counter.number, Counter.name)
            .order_by(Counter.number)
        ).all()
        return [
            {"counter_id": r[0], "number": r[1], "name": r[2], "attended": r[3], "avg_attendance_seconds": _round(r[4])}
            for r in rows
        ]

    @classmethod
    def daily(cls, day: date | None, ticket_type: TicketType | None) -> dict:
        day = day or local_today()
        report = cls.summary(day, day, ticket_type)
        conditions = cls._filters(day, day, ticket_type)
        hours: dict[int, int] = defaultdict(int)
        for (issued_at,) in db.session.execute(select(Ticket.issued_at).where(*conditions)):
            hours[to_local(issued_at).hour] += 1
        report["by_hour"] = [{"hour": h, "issued": hours[h]} for h in sorted(hours)]
        report["date"] = day.isoformat()
        return report

    @classmethod
    def monthly(cls, month: str | None, ticket_type: TicketType | None) -> dict:
        if month:
            year, mon = (int(part) for part in month.split("-"))
        else:
            today = local_today()
            year, mon = today.year, today.month
        start = date(year, mon, 1)
        end = date(year, mon, calendar.monthrange(year, mon)[1])
        report = cls.summary(start, end, ticket_type)
        conditions = cls._filters(start, end, ticket_type)

        issued = dict(
            db.session.execute(select(Ticket.reference_date, func.count(Ticket.id)).where(*conditions).group_by(Ticket.reference_date)).all()
        )
        attended = dict(
            db.session.execute(
                select(Ticket.reference_date, func.count(Ticket.id))
                .where(*conditions, Ticket.status == TicketStatus.ATENDIDA)
                .group_by(Ticket.reference_date)
            ).all()
        )
        not_attended = dict(
            db.session.execute(
                select(Ticket.reference_date, func.count(Ticket.id))
                .where(*conditions, Ticket.status.in_((TicketStatus.NAO_COMPARECEU, TicketStatus.DESCARTADA)))
                .group_by(Ticket.reference_date)
            ).all()
        )
        durations = dict(
            db.session.execute(
                select(Ticket.reference_date, func.avg(Attendance.duration_seconds))
                .join(Attendance, Attendance.ticket_id == Ticket.id)
                .where(*conditions, Attendance.finished_at.is_not(None))
                .group_by(Ticket.reference_date)
            ).all()
        )
        by_day = []
        current = start
        while current <= end:
            by_day.append(
                {
                    "date": current.isoformat(),
                    "issued": issued.get(current, 0),
                    "attended": attended.get(current, 0),
                    "not_attended": not_attended.get(current, 0),
                    "avg_attendance_seconds": _round(durations.get(current)),
                }
            )
            current += timedelta(days=1)
        report["month"] = f"{year:04d}-{mon:02d}"
        report["by_day"] = by_day
        return report

    @staticmethod
    def history(start: date, end: date, ticket_type: TicketType | None, status: TicketStatus | None, page: int, per_page: int):
        conditions = [Ticket.reference_date >= start, Ticket.reference_date <= end]
        if ticket_type:
            conditions.append(Ticket.type == ticket_type)
        if status:
            conditions.append(Ticket.status == status)
        stmt = (
            select(Ticket)
            .where(and_(*conditions))
            .options(
                selectinload(Ticket.calls).selectinload(Call.counter),
                selectinload(Ticket.calls).selectinload(Call.user),
                selectinload(Ticket.attendance).selectinload(Attendance.user),
                selectinload(Ticket.attendance).selectinload(Attendance.counter),
            )
            .order_by(Ticket.issued_at.desc(), Ticket.id.desc())
        )
        tickets, total = paginate(stmt, page, per_page)
        rows = []
        for t in tickets:
            calls = t.calls
            last_call = calls[-1] if calls else None
            att = t.attendance
            attendant = att.user if att else (last_call.user if last_call else None)
            counter = att.counter if att else (last_call.counter if last_call else None)
            rows.append(
                {
                    "ticket_id": t.id,
                    "code": t.code,
                    "type": t.type.value,
                    "type_label": t.type.label,
                    "status": t.status.value,
                    "issued_at": serialize_local(t.issued_at),
                    "first_called_at": serialize_local(calls[0].called_at) if calls else None,
                    "last_called_at": serialize_local(last_call.called_at) if last_call else None,
                    "call_count": len(calls),
                    "started_at": serialize_local(att.started_at) if att else None,
                    "finished_at": serialize_local(att.finished_at) if att else None,
                    "duration_seconds": att.duration_seconds if att else None,
                    "attendant": {"id": attendant.id, "name": attendant.name} if attendant else None,
                    "counter": {"id": counter.id, "number": counter.number, "name": counter.name} if counter else None,
                }
            )
        return rows, total
