"""Hierarquia de exceções de domínio.

Serviços lançam estas exceções; o tratador central (middlewares/error_handlers)
as converte para o formato padronizado de resposta:

    {"error": {"code": "...", "message": "...", "details": ...}}
"""
from __future__ import annotations

from typing import Any


class AppError(Exception):
    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, message: str, *, code: str | None = None, details: Any = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.details = details

    def to_dict(self) -> dict:
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details is not None:
            payload["details"] = self.details
        return {"error": payload}


class ValidationError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"


class AuthenticationError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class PermissionDenied(AppError):
    status_code = 403
    code = "FORBIDDEN"


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class BusinessRuleError(AppError):
    """Violação de regra de negócio (ex.: fora do expediente, fila vazia)."""

    status_code = 422
    code = "BUSINESS_RULE_VIOLATION"


class InvalidTransitionError(BusinessRuleError):
    code = "INVALID_STATUS_TRANSITION"
