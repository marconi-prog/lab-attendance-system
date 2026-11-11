"""Regras de horário de funcionamento (fuso America/Recife)."""
from __future__ import annotations

from datetime import datetime, time

from flask import current_app

from app.utils.clock import local_now
from app.utils.errors import BusinessRuleError


class BusinessHours:
    @staticmethod
    def _cfg(key: str):
        return current_app.config[key]

    @classmethod
    def enforced(cls) -> bool:
        return bool(cls._cfg("ENFORCE_BUSINESS_HOURS"))

    @classmethod
    def open_time(cls) -> time:
        return cls._cfg("BUSINESS_OPEN_TIME")

    @classmethod
    def close_time(cls) -> time:
        return cls._cfg("BUSINESS_CLOSE_TIME")

    @classmethod
    def is_calling_allowed(cls, at: datetime | None = None) -> bool:
        if not cls.enforced():
            return True
        current = (at or local_now()).time()
        return cls.open_time() <= current < cls.close_time()

    @classmethod
    def is_issuing_allowed(cls, at: datetime | None = None) -> bool:
        if not cls.enforced():
            return True
        current = (at or local_now()).time()
        return cls._cfg("TICKET_ISSUE_OPEN_TIME") <= current < cls.close_time()

    @classmethod
    def is_after_close(cls, at: datetime | None = None) -> bool:
        return (at or local_now()).time() >= cls.close_time()

    @classmethod
    def ensure_calling_allowed(cls) -> None:
        if not cls.is_calling_allowed():
            raise BusinessRuleError(
                f"Chamadas permitidas somente entre {cls.open_time():%H:%M} e {cls.close_time():%H:%M}.",
                code="OUTSIDE_BUSINESS_HOURS",
            )

    @classmethod
    def ensure_issuing_allowed(cls) -> None:
        if not cls.is_issuing_allowed():
            raise BusinessRuleError(
                "Emissão de senhas indisponível: o laboratório está fora do horário de atendimento.",
                code="OUTSIDE_BUSINESS_HOURS",
            )

    @classmethod
    def describe(cls) -> dict:
        return {
            "open": f"{cls.open_time():%H:%M}",
            "close": f"{cls.close_time():%H:%M}",
            "issue_open": f"{cls._cfg('TICKET_ISSUE_OPEN_TIME'):%H:%M}",
            "enforced": cls.enforced(),
            "timezone": cls._cfg("TIMEZONE"),
            "calling_allowed_now": cls.is_calling_allowed(),
            "issuing_allowed_now": cls.is_issuing_allowed(),
        }
