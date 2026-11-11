"""Tratamento centralizado de exceções — toda resposta de erro tem o mesmo formato."""
from __future__ import annotations

import logging

from flask import Flask, jsonify
from sqlalchemy.exc import IntegrityError, OperationalError
from werkzeug.exceptions import HTTPException

from app.extensions import db
from app.utils.errors import AppError

logger = logging.getLogger(__name__)


def _error(status: int, code: str, message: str, details=None):
    body = {"code": code, "message": message}
    if details is not None:
        body["details"] = details
    return jsonify({"error": body}), status


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AppError)
    def handle_app_error(exc: AppError):
        return jsonify(exc.to_dict()), exc.status_code

    @app.errorhandler(HTTPException)
    def handle_http(exc: HTTPException):
        code = (exc.name or "HTTP_ERROR").upper().replace(" ", "_")
        messages = {404: "Recurso não encontrado.", 405: "Método não permitido.", 415: "Content-Type deve ser application/json."}
        return _error(exc.code or 500, code, messages.get(exc.code, exc.description or exc.name))

    @app.errorhandler(IntegrityError)
    def handle_integrity(exc: IntegrityError):
        db.session.rollback()
        logger.warning("Violação de integridade: %s", exc.orig.__class__.__name__)
        return _error(409, "INTEGRITY_ERROR", "A operação viola uma restrição de integridade dos dados.")

    @app.errorhandler(OperationalError)
    def handle_db_unavailable(exc: OperationalError):
        db.session.rollback()
        logger.error("Erro operacional do banco de dados: %s", exc.orig.__class__.__name__)
        return _error(503, "DATABASE_UNAVAILABLE", "Banco de dados indisponível. Tente novamente em instantes.")

    @app.errorhandler(Exception)
    def handle_unexpected(exc: Exception):
        db.session.rollback()
        logger.exception("Erro não tratado")
        return _error(500, "INTERNAL_ERROR", "Erro interno do servidor.")
