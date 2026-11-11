"""Indicadores do dia para o gestor e informações gerais do sistema."""
from __future__ import annotations

from flask import current_app
from sqlalchemy import func, select, text

from app.extensions import db
from app.models import Counter, TicketStatus, User
from app.models.enums import ACTIVE_STATUSES
from app.repositories import CounterRepository, TicketRepository
from app.schemas.common import serialize_local
from app.services.business_hours import BusinessHours
from app.services.panel_service import PanelService
from app.services.queue_service import QueueService
from app.services.report_service import ReportService
from app.utils.clock import local_now, local_today


class DashboardService:
    @staticmethod
    def overview() -> dict:
        today = local_today()
        status_counts = TicketRepository.status_counts(today)
        report = ReportService.summary(today, today)
        sessions = []
        for s in CounterRepository.open_sessions():
            current = TicketRepository.active_ticket_for_counter(s.counter_id)
            sessions.append(
                {
                    "session_id": s.id,
                    "counter": {"id": s.counter.id, "number": s.counter.number, "name": s.counter.name},
                    "attendant": {"id": s.user.id, "name": s.user.name},
                    "opened_at": serialize_local(s.opened_at),
                    "current_ticket": (
                        {"id": current.id, "code": current.short_code, "status": current.status.value} if current else None
                    ),
                }
            )
        return {
            "date": today.isoformat(),
            "issued": sum(status_counts.values()),
            "attended": status_counts[TicketStatus.ATENDIDA],
            "waiting": status_counts[TicketStatus.AGUARDANDO],
            "in_progress": sum(status_counts[s] for s in ACTIVE_STATUSES),
            "no_show": status_counts[TicketStatus.NAO_COMPARECEU],
            "discarded": status_counts[TicketStatus.DESCARTADA],
            "by_status": {s.value: n for s, n in status_counts.items()},
            "avg_attendance_seconds": report["totals"]["avg_attendance_seconds"],
            "avg_wait_seconds": report["totals"]["avg_wait_seconds"],
            "by_type": report["by_type"],
            "queue": QueueService.summary(),
            "open_sessions": sessions,
            "recent_calls": PanelService.latest(),
            "business_hours": BusinessHours.describe(),
        }

    @staticmethod
    def system_info() -> dict:
        db_version = db.session.execute(text("SELECT VERSION()")).scalar()
        return {
            "app_name": current_app.config["APP_NAME"],
            "version": current_app.config["APP_VERSION"],
            "lab_name": current_app.config["LAB_NAME"],
            "environment": "testing" if current_app.config["TESTING"] else ("development" if current_app.debug else "production"),
            "server_time": local_now().isoformat(timespec="seconds"),
            "database": {"engine": "MySQL", "version": db_version},
            "business_hours": BusinessHours.describe(),
            "counts": {
                "users": db.session.scalar(select(func.count(User.id))),
                "active_users": db.session.scalar(select(func.count(User.id)).where(User.active.is_(True))),
                "counters": db.session.scalar(select(func.count(Counter.id))),
                "active_counters": db.session.scalar(select(func.count(Counter.id)).where(Counter.active.is_(True))),
                "open_sessions": len(CounterRepository.open_sessions()),
            },
        }
