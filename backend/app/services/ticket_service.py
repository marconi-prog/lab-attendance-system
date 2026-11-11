"""Emissão de senhas pelo totem."""
from __future__ import annotations

from flask import current_app
from sqlalchemy import func, select

from app.extensions import db
from app.models import Ticket, TicketStatus, TicketStatusHistory, TicketType
from app.repositories import TicketRepository
from app.services.audit_service import AuditService
from app.services.business_hours import BusinessHours
from app.services.realtime import Events, RealtimeNotifier
from app.services.state_machine import TicketStateMachine
from app.utils.clock import local_today, utcnow
from app.utils.db import paginate, run_in_transaction
from app.utils.errors import BusinessRuleError, NotFoundError


def format_ticket_code(reference_date, ticket_type: TicketType, sequence: int) -> str:
    """Padrão YYMMDD-PPSQ, ex.: 261110-SP001."""
    return f"{reference_date:%y%m%d}-{ticket_type.value}{sequence:03d}"


class TicketService:
    @staticmethod
    def issue(ticket_type: TicketType) -> tuple[Ticket, int]:
        """Emite uma senha de forma atômica.

        A linha de daily_sequences do dia/categoria é bloqueada com
        SELECT ... FOR UPDATE: emissões simultâneas da mesma categoria são
        serializadas e cada uma recebe um número distinto. A unique
        constraint em tickets.code é a última barreira contra duplicidade.
        """
        BusinessHours.ensure_issuing_allowed()
        today = local_today()
        max_seq = current_app.config["MAX_DAILY_SEQUENCE"]
        TicketRepository.ensure_sequence_row(today, ticket_type)

        def tx() -> Ticket:
            sequence_row = TicketRepository.lock_sequence(today, ticket_type)
            if sequence_row.last_sequence >= max_seq:
                raise BusinessRuleError(
                    f"Limite diário de {max_seq} senhas da categoria {ticket_type.value} atingido.",
                    code="DAILY_LIMIT_REACHED",
                )
            sequence_row.last_sequence += 1
            sequence = sequence_row.last_sequence
            now = utcnow()
            ticket = Ticket(
                code=format_ticket_code(today, ticket_type, sequence),
                type=ticket_type,
                status=TicketStatus.EMITIDA,
                daily_sequence=sequence,
                reference_date=today,
                issued_at=now,
                updated_at=now,
            )
            db.session.add(ticket)
            db.session.flush()
            db.session.add(TicketStatusHistory(ticket_id=ticket.id, from_status=None, to_status=TicketStatus.EMITIDA, created_at=now))
            TicketStateMachine.transition(ticket, TicketStatus.AGUARDANDO)
            AuditService.record("TICKET_ISSUED", "ticket", ticket.id, details={"code": ticket.code, "type": ticket_type.value})
            return ticket

        ticket = run_in_transaction(tx)
        waiting_ahead = TicketService.waiting_ahead(ticket)

        from app.services.panel_service import PanelService
        from app.services.presenters import ticket_payload
        from app.services.queue_service import QueueService

        RealtimeNotifier.to_staff(Events.TICKET_ISSUED, {"ticket": ticket_payload(ticket)})
        RealtimeNotifier.to_staff(Events.QUEUE_UPDATED, QueueService.summary())
        PanelService.publish()  # a nova senha entra na coluna "Aguardando" do painel
        return ticket, waiting_ahead

    @staticmethod
    def waiting_ahead(ticket: Ticket) -> int:
        return db.session.scalar(
            select(func.count(Ticket.id)).where(
                Ticket.status == TicketStatus.AGUARDANDO,
                Ticket.reference_date == ticket.reference_date,
                Ticket.type == ticket.type,
                Ticket.id < ticket.id,
            )
        ) or 0

    @staticmethod
    def get_detail(ticket_id: int) -> Ticket:
        ticket = TicketRepository.get_with_details(ticket_id)
        if not ticket:
            raise NotFoundError("Senha não encontrada.")
        return ticket

    @staticmethod
    def list(query):
        stmt = TicketRepository.list(reference_date=query.day, status=query.status, ticket_type=query.type)
        return paginate(stmt, query.page, query.per_page)
