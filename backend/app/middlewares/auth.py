"""Integração JWT: identidade, revogação e erros no formato padrão."""
from __future__ import annotations

from flask import Flask, jsonify

from app.extensions import jwt
from app.models import User
from app.repositories import UserRepository


def _unauthorized(message: str, code: str = "UNAUTHORIZED", status: int = 401):
    return jsonify({"error": {"code": code, "message": message}}), status


def register_jwt_callbacks(app: Flask) -> None:
    @jwt.user_identity_loader
    def user_identity(user: User | int | str) -> str:
        return str(user.id if isinstance(user, User) else user)

    @jwt.user_lookup_loader
    def user_lookup(_header, payload) -> User | None:
        user = UserRepository.get(int(payload["sub"]))
        # Usuário desativado perde o acesso imediatamente, mesmo com token válido.
        return user if user and user.active else None

    @jwt.token_in_blocklist_loader
    def token_revoked(_header, payload) -> bool:
        from app.services.auth_service import AuthService

        return AuthService.is_token_revoked(payload["jti"])

    @jwt.user_lookup_error_loader
    def lookup_error(_header, _payload):
        return _unauthorized("Usuário inexistente ou desativado.", "USER_INACTIVE")

    @jwt.expired_token_loader
    def expired(_header, _payload):
        return _unauthorized("Sessão expirada. Faça login novamente.", "TOKEN_EXPIRED")

    @jwt.invalid_token_loader
    def invalid(reason: str):
        return _unauthorized("Token inválido.", "TOKEN_INVALID")

    @jwt.unauthorized_loader
    def missing(reason: str):
        return _unauthorized("Autenticação necessária.", "UNAUTHORIZED")

    @jwt.revoked_token_loader
    def revoked(_header, _payload):
        return _unauthorized("Token revogado. Faça login novamente.", "TOKEN_REVOKED")

    @jwt.needs_fresh_token_loader
    def needs_fresh(_header, _payload):
        return _unauthorized("Reautenticação necessária.", "FRESH_TOKEN_REQUIRED")
