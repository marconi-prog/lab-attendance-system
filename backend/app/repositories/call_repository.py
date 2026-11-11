from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import Call


class CallRepository:
    @staticmethod
    def recent_since(since_utc: datetime, limit: int) -> list[Call]:
        return list(
            db.session.scalars(
                select(Call)
                .where(Call.called_at >= since_utc)
                .options(joinedload(Call.ticket), joinedload(Call.counter))
                .order_by(Call.called_at.desc(), Call.id.desc())
                .limit(limit)
            )
        )

    @staticmethod
    def last_for_ticket(ticket_id: int) -> Call | None:
        return db.session.scalars(
            select(Call).where(Call.ticket_id == ticket_id).order_by(Call.attempt_number.desc()).limit(1)
        ).first()
