from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import User, UserRole


class UserRepository:
    @staticmethod
    def get(user_id: int) -> User | None:
        return db.session.get(User, user_id)

    @staticmethod
    def get_by_email(email: str) -> User | None:
        return db.session.scalars(select(User).where(func.lower(User.email) == email.lower())).first()

    @staticmethod
    def list(*, search: str | None, role: UserRole | None, active: bool | None):
        stmt = select(User).options(selectinload(User.counters)).order_by(User.name)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(or_(User.name.ilike(like), User.email.ilike(like)))
        if role:
            stmt = stmt.where(User.role == role)
        if active is not None:
            stmt = stmt.where(User.active.is_(active))
        return stmt

    @staticmethod
    def count_active_admins() -> int:
        return db.session.scalar(
            select(func.count(User.id)).where(User.role == UserRole.ADMIN, User.active.is_(True))
        ) or 0
