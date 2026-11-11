from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models import AuditLog


class AuditRepository:
    @staticmethod
    def list(
        *,
        user_id: int | None,
        action: str | None,
        entity: str | None,
        start_utc: datetime | None,
        end_utc: datetime | None,
    ):
        stmt = select(AuditLog).options(joinedload(AuditLog.user)).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        if user_id:
            stmt = stmt.where(AuditLog.user_id == user_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if entity:
            stmt = stmt.where(AuditLog.entity == entity)
        if start_utc:
            stmt = stmt.where(AuditLog.created_at >= start_utc)
        if end_utc:
            stmt = stmt.where(AuditLog.created_at < end_utc)
        return stmt
