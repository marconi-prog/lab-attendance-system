from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.mixins import TimestampMixin
from app.models.user import user_counters
from app.utils.clock import utcnow

if TYPE_CHECKING:
    from app.models.user import User


class Counter(TimestampMixin, db.Model):
    """Guichê de atendimento."""

    __tablename__ = "counters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    users: Mapped[list["User"]] = relationship(secondary=user_counters, back_populates="counters")

    @property
    def label(self) -> str:
        return f"{self.number:02d}"


class CounterSession(db.Model):
    """Ocupação de um guichê por um atendente (abre ao entrar, fecha ao sair).

    Garante que um guichê seja operado por apenas um atendente por vez e
    que um atendente opere apenas um guichê por vez. A exclusividade é
    garantida por bloqueio (SELECT ... FOR UPDATE) na abertura da sessão.
    """

    __tablename__ = "counter_sessions"
    __table_args__ = (
        Index("ix_counter_sessions_counter_closed", "counter_id", "closed_at"),
        Index("ix_counter_sessions_user_closed", "user_id", "closed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    counter_id: Mapped[int] = mapped_column(ForeignKey("counters.id", ondelete="RESTRICT"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    counter: Mapped[Counter] = relationship()
    user: Mapped["User"] = relationship()
