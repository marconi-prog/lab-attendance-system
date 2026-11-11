from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Table, Column
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


class User(TimestampMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(sa_enum(UserRole, "user_role"), nullable=False, index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    counters: Mapped[list["Counter"]] = relationship(secondary=user_counters, back_populates="users", order_by="Counter.number")

    def set_password(self, raw_password: str) -> None:
        # scrypt (padrão do Werkzeug 3) — hash com salt aleatório.
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def __repr__(self) -> str:  # nunca expõe o hash
        return f"<User id={self.id} role={self.role.value}>"
