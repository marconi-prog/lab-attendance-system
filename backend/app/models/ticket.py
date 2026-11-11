from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.enums import AttendanceResult, TicketStatus, TicketType, sa_enum
from app.utils.clock import utcnow

if TYPE_CHECKING:
    from app.models.counter import Counter
    from app.models.user import User


class DailySequence(db.Model):
    """Último número emitido por categoria em cada dia (reinicia diariamente)."""

    __tablename__ = "daily_sequences"
    __table_args__ = (UniqueConstraint("reference_date", "ticket_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    reference_date: Mapped[date] = mapped_column(Date, nullable=False)
    ticket_type: Mapped[TicketType] = mapped_column(sa_enum(TicketType, "ticket_type"), nullable=False)
    last_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class QueueState(db.Model):
    """Estado do ciclo de prioridade do dia.

    A linha do dia é bloqueada (FOR UPDATE) a cada "chamar próxima",
    serializando a seleção entre guichês e evitando que dois atendentes
    recebam a mesma senha.
    """

    __tablename__ = "queue_states"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    last_called_type: Mapped[TicketType | None] = mapped_column(sa_enum(TicketType, "ticket_type"), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class Ticket(db.Model):
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("reference_date", "type", "daily_sequence"),
        # Seleção da próxima senha: WHERE status=? AND reference_date=? AND type=? ORDER BY issued_at, id
        Index("ix_tickets_queue", "status", "reference_date", "type", "issued_at", "id"),
        Index("ix_tickets_reference_date_type", "reference_date", "type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    type: Mapped[TicketType] = mapped_column(sa_enum(TicketType, "ticket_type"), nullable=False)
    status: Mapped[TicketStatus] = mapped_column(sa_enum(TicketStatus, "ticket_status"), nullable=False)
    daily_sequence: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    reference_date: Mapped[date] = mapped_column(Date, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    calls: Mapped[list["Call"]] = relationship(back_populates="ticket", order_by="Call.attempt_number")
    attendance: Mapped["Attendance | None"] = relationship(back_populates="ticket", uselist=False)
    status_history: Mapped[list["TicketStatusHistory"]] = relationship(
        back_populates="ticket", order_by="TicketStatusHistory.id"
    )

    @property
    def short_code(self) -> str:
        """Parte exibida ao público, ex.: SP001."""
        return self.code.split("-", 1)[1]


class TicketStatusHistory(db.Model):
    """Trilha imutável de todas as transições de estado de cada senha."""

    __tablename__ = "ticket_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status: Mapped[TicketStatus | None] = mapped_column(sa_enum(TicketStatus, "ticket_status"), nullable=True)
    to_status: Mapped[TicketStatus] = mapped_column(sa_enum(TicketStatus, "ticket_status"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    counter_id: Mapped[int | None] = mapped_column(ForeignKey("counters.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    ticket: Mapped[Ticket] = relationship(back_populates="status_history")
    user: Mapped["User | None"] = relationship()


class Call(db.Model):
    """Cada chamada (ou repetição) é um registro novo — o histórico nunca é sobrescrito."""

    __tablename__ = "calls"
    __table_args__ = (UniqueConstraint("ticket_id", "attempt_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    counter_id: Mapped[int] = mapped_column(ForeignKey("counters.id", ondelete="RESTRICT"), nullable=False, index=True)
    attempt_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    called_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, index=True)

    ticket: Mapped[Ticket] = relationship(back_populates="calls")
    user: Mapped["User"] = relationship()
    counter: Mapped["Counter"] = relationship()


class Attendance(db.Model):
    __tablename__ = "attendances"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    counter_id: Mapped[int] = mapped_column(ForeignKey("counters.id", ondelete="RESTRICT"), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result: Mapped[AttendanceResult] = mapped_column(
        sa_enum(AttendanceResult, "attendance_result"), nullable=False, default=AttendanceResult.EM_ANDAMENTO
    )

    ticket: Mapped[Ticket] = relationship(back_populates="attendance")
    user: Mapped["User"] = relationship()
    counter: Mapped["Counter"] = relationship()
