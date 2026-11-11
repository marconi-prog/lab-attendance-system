from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import Counter, CounterSession


class CounterRepository:
    @staticmethod
    def get(counter_id: int) -> Counter | None:
        return db.session.get(Counter, counter_id)

    @staticmethod
    def get_for_update(counter_id: int) -> Counter | None:
        return db.session.scalars(select(Counter).where(Counter.id == counter_id).with_for_update()).first()

    @staticmethod
    def get_by_number(number: int) -> Counter | None:
        return db.session.scalars(select(Counter).where(Counter.number == number)).first()

    @staticmethod
    def list(*, active: bool | None = None) -> list[Counter]:
        stmt = select(Counter).order_by(Counter.number)
        if active is not None:
            stmt = stmt.where(Counter.active.is_(active))
        return list(db.session.scalars(stmt))

    @staticmethod
    def get_many(ids: list[int]) -> list[Counter]:
        return list(db.session.scalars(select(Counter).where(Counter.id.in_(ids))))

    # ---------- sessões ----------
    @staticmethod
    def open_session_for_counter(counter_id: int) -> CounterSession | None:
        return db.session.scalars(
            select(CounterSession)
            .where(CounterSession.counter_id == counter_id, CounterSession.closed_at.is_(None))
            .options(joinedload(CounterSession.user))
        ).first()

    @staticmethod
    def open_session_for_user(user_id: int) -> CounterSession | None:
        return db.session.scalars(
            select(CounterSession)
            .where(CounterSession.user_id == user_id, CounterSession.closed_at.is_(None))
            .options(joinedload(CounterSession.counter))
        ).first()

    @staticmethod
    def open_sessions() -> list[CounterSession]:
        return list(
            db.session.scalars(
                select(CounterSession)
                .where(CounterSession.closed_at.is_(None))
                .options(joinedload(CounterSession.counter), joinedload(CounterSession.user))
            )
        )
