"""Consultas de senhas, sequência diária e estado da fila."""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.enums import ACTIVE_STATUSES
from app.models import (
    Attendance,
    Call,
    DailySequence,
    QueueState,
    Ticket,
    TicketStatus,
    TicketType,
)


class TicketRepository:
    # ---------- sequência diária ----------
    @staticmethod
    def ensure_sequence_row(reference_date: date, ticket_type: TicketType) -> None:
        """Cria a linha do contador do dia, se ainda não existir.

        Executado em transação própria e curta (INSERT IGNORE + commit), para
        que a transação de emissão só precise de um bloqueio exclusivo simples
        sobre uma linha existente — sem gap locks e sem deadlocks.
        """
        stmt = mysql_insert(DailySequence).values(
            reference_date=reference_date, ticket_type=ticket_type, last_sequence=0
        ).prefix_with("IGNORE")
        db.session.execute(stmt)
        db.session.commit()

    @staticmethod
    def lock_sequence(reference_date: date, ticket_type: TicketType) -> DailySequence:
        return db.session.scalars(
            select(DailySequence)
            .where(DailySequence.reference_date == reference_date, DailySequence.ticket_type == ticket_type)
            .with_for_update()
        ).one()

    # ---------- estado da fila ----------
    @staticmethod
    def ensure_queue_state(reference_date: date) -> None:
        db.session.execute(mysql_insert(QueueState).values(reference_date=reference_date).prefix_with("IGNORE"))
        db.session.commit()

    @staticmethod
    def lock_queue_state(reference_date: date) -> QueueState:
        return db.session.scalars(
            select(QueueState).where(QueueState.reference_date == reference_date).with_for_update()
        ).one()

    @staticmethod
    def get_queue_state(reference_date: date) -> QueueState | None:
        return db.session.scalars(select(QueueState).where(QueueState.reference_date == reference_date)).first()

    # ---------- consultas ----------
    @staticmethod
    def get(ticket_id: int) -> Ticket | None:
        return db.session.get(Ticket, ticket_id)

    @staticmethod
    def get_for_update(ticket_id: int) -> Ticket | None:
        return db.session.scalars(select(Ticket).where(Ticket.id == ticket_id).with_for_update()).first()

    @staticmethod
    def get_with_details(ticket_id: int) -> Ticket | None:
        return db.session.scalars(
            select(Ticket)
            .where(Ticket.id == ticket_id)
            .options(
                selectinload(Ticket.calls).selectinload(Call.counter),
                selectinload(Ticket.calls).selectinload(Call.user),
                selectinload(Ticket.attendance).selectinload(Attendance.user),
                selectinload(Ticket.status_history),
            )
        ).first()

    @staticmethod
    def waiting_counts(reference_date: date) -> dict[TicketType, int]:
        rows = db.session.execute(
            select(Ticket.type, func.count(Ticket.id))
            .where(Ticket.status == TicketStatus.AGUARDANDO, Ticket.reference_date == reference_date)
            .group_by(Ticket.type)
        ).all()
        counts = {t: 0 for t in TicketType}
        counts.update({row[0]: row[1] for row in rows})
        return counts

    @staticmethod
    def lock_next_waiting(reference_date: date, ticket_type: TicketType) -> Ticket | None:
        """Primeira senha da categoria (FIFO), bloqueada para este guichê.

        SKIP LOCKED faz uma transação concorrente pular linhas já reservadas.
        """
        return db.session.scalars(
            select(Ticket)
            .where(
                Ticket.status == TicketStatus.AGUARDANDO,
                Ticket.reference_date == reference_date,
                Ticket.type == ticket_type,
            )
            .order_by(Ticket.issued_at, Ticket.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        ).first()

    @staticmethod
    def waiting_by_type(reference_date: date, limit_per_type: int) -> dict[TicketType, list[Ticket]]:
        """Próximas senhas de cada fila, na ordem de atendimento (FIFO). Usa ix_tickets_queue."""
        return {
            ticket_type: list(
                db.session.scalars(
                    select(Ticket)
                    .where(
                        Ticket.status == TicketStatus.AGUARDANDO,
                        Ticket.reference_date == reference_date,
                        Ticket.type == ticket_type,
                    )
                    .order_by(Ticket.issued_at, Ticket.id)
                    .limit(limit_per_type)
                )
            )
            for ticket_type in TicketType
        }

    @staticmethod
    def in_service(reference_date: date) -> list[tuple[Ticket, int]]:
        """Senhas em atendimento agora, com o número do guichê."""
        from app.models import Attendance, Counter

        rows = db.session.execute(
            select(Ticket, Counter.number)
            .join(Attendance, Attendance.ticket_id == Ticket.id)
            .join(Counter, Counter.id == Attendance.counter_id)
            .where(Ticket.status == TicketStatus.EM_ATENDIMENTO, Ticket.reference_date == reference_date)
            .order_by(Attendance.started_at)
        ).all()
        return [(row[0], row[1]) for row in rows]

    @staticmethod
    def active_ticket_for_counter(counter_id: int) -> Ticket | None:
        """Senha atualmente chamada/em atendimento neste guichê."""
        last_call_counter = (
            select(Call.counter_id)
            .where(Call.ticket_id == Ticket.id)
            .order_by(Call.attempt_number.desc())
            .limit(1)
            .correlate(Ticket)
            .scalar_subquery()
        )
        return db.session.scalars(
            select(Ticket)
            .where(Ticket.status.in_(ACTIVE_STATUSES), last_call_counter == counter_id)
            .order_by(Ticket.updated_at.desc())
            .limit(1)
        ).first()

    @staticmethod
    def lock_waiting_until(reference_date: date) -> list[Ticket]:
        """Senhas ainda aguardando do dia informado e anteriores (bloqueadas)."""
        return list(
            db.session.scalars(
                select(Ticket)
                .where(Ticket.status == TicketStatus.AGUARDANDO, Ticket.reference_date <= reference_date)
                .with_for_update()
            )
        )

    @staticmethod
    def count_waiting_until(reference_date: date) -> int:
        return db.session.scalar(
            select(func.count(Ticket.id)).where(
                Ticket.status == TicketStatus.AGUARDANDO, Ticket.reference_date <= reference_date
            )
        ) or 0

    @staticmethod
    def list(*, reference_date: date | None, status: TicketStatus | None, ticket_type: TicketType | None):
        stmt = select(Ticket).order_by(Ticket.issued_at.desc(), Ticket.id.desc())
        if reference_date:
            stmt = stmt.where(Ticket.reference_date == reference_date)
        if status:
            stmt = stmt.where(Ticket.status == status)
        if ticket_type:
            stmt = stmt.where(Ticket.type == ticket_type)
        return stmt

    @staticmethod
    def status_counts(reference_date: date) -> dict[TicketStatus, int]:
        rows = db.session.execute(
            select(Ticket.status, func.count(Ticket.id))
            .where(Ticket.reference_date == reference_date)
            .group_by(Ticket.status)
        ).all()
        counts = {s: 0 for s in TicketStatus}
        counts.update({row[0]: row[1] for row in rows})
        return counts
