"""Registro de auditoria. Sempre gravado na mesma transação da operação."""
from __future__ import annotations

from typing import Any

from flask import has_request_context, request

from app.extensions import db
from app.models import AuditLog
from app.utils.clock import utcnow

# Campos que nunca podem ir para a auditoria.
_SENSITIVE_KEYS = {"password", "password_hash", "new_password", "current_password", "token", "refresh_token", "access_token"}


def _sanitize(details: dict[str, Any] | None) -> dict[str, Any] | None:
    if not details:
        return None
    return {k: ("***" if k in _SENSITIVE_KEYS else v) for k, v in details.items()}


class AuditService:
    @staticmethod
    def record(
        action: str,
        entity: str,
        entity_id: Any = None,
        *,
        user_id: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        ip = None
        if has_request_context():
            ip = (request.headers.get("X-Forwarded-For", request.remote_addr) or "").split(",")[0].strip()[:45] or None
        log = AuditLog(
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=_sanitize(details),
            ip_address=ip,
            created_at=utcnow(),
        )
        db.session.add(log)
        return log
