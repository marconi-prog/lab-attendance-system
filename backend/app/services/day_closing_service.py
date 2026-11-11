"""Encerramento do expediente: senhas ainda aguardando são DESCARTADAS.

Senhas já chamadas ou em atendimento não são afetadas — podem ser
concluídas mesmo após as 17h.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from app.models import TicketStatus
from app.repositories import TicketRepository
from app.services.audit_service import AuditService
from app.services.business_hours import BusinessHours
from app.services.state_machine import TicketStateMachine
from app.utils.clock import local_today, utcnow
from app.utils.db import run_in_transaction

logger = logging.getLogger(__name__)


class DayClosingService:
    @staticmethod
    def discard_waiting(up_to: date, *, user_id: int | None, mark_closed: bool) -> int:
        TicketRepository.ensure_queue_state(up_to)

        def tx() -> int:
            state = TicketRepository.lock_queue_state(up_to)  # bloqueia novas chamadas durante o descarte
            tickets = TicketRepository.lock_waiting_until(up_to)
            for ticket in tickets:
                TicketStateMachine.transition(ticket, TicketStatus.DESCARTADA, user_id=user_id)
            if mark_closed and state.closed_at is None:
                state.closed_at = utcnow()
            AuditService.record(
                "DAY_CLOSED" if mark_closed else "STALE_TICKETS_DISCARDED",
                "queue", up_to.isoformat(), user_id=user_id, details={"discarded": len(tickets)},
            )
            return len(tickets)

        discarded = run_in_transaction(tx)
        if discarded:
            from app.services.queue_service import QueueService
            from app.services.realtime import Events, RealtimeNotifier

            from app.services.panel_service import PanelService

            RealtimeNotifier.to_staff(Events.QUEUE_UPDATED, QueueService.summary())
            PanelService.publish()
        return discarded

    @classmethod
    def close_today(cls, *, user_id: int | None = None) -> int:
        return cls.discard_waiting(local_today(), user_id=user_id, mark_closed=True)

    @classmethod
    def run_scheduled(cls) -> None:
        """Rotina periódica: descarta pendências de dias anteriores e fecha o dia após o expediente."""
        today = local_today()
        yesterday = today - timedelta(days=1)
        if TicketRepository.count_waiting_until(yesterday):
            count = cls.discard_waiting(yesterday, user_id=None, mark_closed=False)
            logger.info("Descartadas %s senhas pendentes de dias anteriores", count)
        if BusinessHours.enforced() and BusinessHours.is_after_close():
            state = TicketRepository.get_queue_state(today)
            if state is None or state.closed_at is None:
                count = cls.close_today()
                logger.info("Expediente encerrado: %s senhas descartadas", count)
