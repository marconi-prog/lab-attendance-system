from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, Computed, ForeignKey, Index, SmallInteger, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models.enums import UserRole, sa_enum
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.counter import Counter

# Associação N:N — quais guichês cada atendente está autorizado a operar.
user_counters = Table(
    "user_counters",
    db.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("counter_id", ForeignKey("counters.id", ondelete="CASCADE"), primary_key=True),
)

# Gestor ativo único, garantido pelo próprio banco (vale também para escritas
# diretas e operações concorrentes): a coluna calculada vale 1 apenas para um
# ADMIN ativo e NULL para os demais; o índice único aceita vários NULL, mas um
# único 1. Mesma expressão na migração 0002 (MySQL 8 e SQLite).
ACTIVE_MANAGER_SLOT_SQL = "CASE WHEN role = 'ADMIN' AND active THEN 1 ELSE NULL END"
ACTIVE_MANAGER_INDEX = "uq_users_active_manager_slot"


class User(TimestampMixin, db.Model):
    __tablename__ = "users"
    __table_args__ = (Index(ACTIVE_MANAGER_INDEX, "active_manager_slot", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(sa_enum(UserRole, "user_role"), nullable=False, index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    active_manager_slot: Mapped[int | None] = mapped_column(
        SmallInteger, Computed(ACTIVE_MANAGER_SLOT_SQL, persisted=False), nullable=True
    )

    counters: Mapped[list["Counter"]] = relationship(secondary=user_counters, back_populates="users", order_by="Counter.number")

    def set_password(self, raw_password: str) -> None:
        # scrypt (padrão do Werkzeug 3) — hash com salt aleatório.
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def __repr__(self) -> str:  # nunca expõe o hash
        return f"<User id={self.id} role={self.role.value}>"


def is_active_manager_conflict(exc: BaseException) -> bool:
    """IntegrityError causado pelo índice de gestor ativo único (MySQL: nome do índice; SQLite: coluna)."""
    return "active_manager_slot" in str(getattr(exc, "orig", exc))
