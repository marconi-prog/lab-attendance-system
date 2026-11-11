from __future__ import annotations

from datetime import datetime, timezone

from flask_jwt_extended import create_access_token, create_refresh_token, decode_token
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import TokenBlocklist, User
from app.repositories import UserRepository
from app.services.audit_service import AuditService
from app.utils.db import run_in_transaction
from app.utils.errors import AuthenticationError, ValidationError

# Hash descartável usado quando o e-mail não existe: mantém o tempo de
# resposta semelhante e dificulta a enumeração de usuários.
_DUMMY_HASH = generate_password_hash("dummy-password-for-timing")


def _claims(user: User) -> dict:
    return {"role": user.role.value, "name": user.name}


class AuthService:
    @staticmethod
    def login(email: str, password: str) -> tuple[User, str, str]:
        user = UserRepository.get_by_email(email)
        valid = check_password_hash(user.password_hash if user else _DUMMY_HASH, password)
        if not user or not valid or not user.active:
            if user:
                run_in_transaction(
                    lambda: AuditService.record("LOGIN_FAILED", "user", user.id, user_id=user.id)
                )
            raise AuthenticationError("E-mail ou senha inválidos.", code="INVALID_CREDENTIALS")

        access = create_access_token(identity=user, additional_claims=_claims(user))
        refresh = create_refresh_token(identity=user)
        run_in_transaction(lambda: AuditService.record("LOGIN", "user", user.id, user_id=user.id))
        return user, access, refresh

    @staticmethod
    def refresh(user: User) -> str:
        return create_access_token(identity=user, additional_claims=_claims(user))

    @staticmethod
    def _revoke(decoded: dict) -> None:
        if db.session.query(TokenBlocklist.id).filter_by(jti=decoded["jti"]).first():
            return
        db.session.add(
            TokenBlocklist(
                jti=decoded["jti"],
                token_type=decoded.get("type", "access"),
                user_id=int(decoded["sub"]),
                expires_at=datetime.fromtimestamp(decoded["exp"], tz=timezone.utc).replace(tzinfo=None),
            )
        )

    @classmethod
    def logout(cls, user: User, access_jwt: dict, refresh_token: str | None) -> None:
        def tx() -> None:
            cls._revoke(access_jwt)
            if refresh_token:
                try:
                    decoded = decode_token(refresh_token)
                except Exception:
                    decoded = None
                if decoded and decoded.get("type") == "refresh" and decoded.get("sub") == access_jwt.get("sub"):
                    cls._revoke(decoded)
            AuditService.record("LOGOUT", "user", user.id, user_id=user.id)

        run_in_transaction(tx)

    @staticmethod
    def change_password(user: User, current: str, new: str) -> None:
        if not user.check_password(current):
            raise ValidationError("Senha atual incorreta.", code="INVALID_PASSWORD")
        from app.schemas.user import validate_password_strength

        try:
            validate_password_strength(new)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        def tx() -> None:
            user.set_password(new)
            AuditService.record("PASSWORD_CHANGED", "user", user.id, user_id=user.id)

        run_in_transaction(tx)

    @staticmethod
    def is_token_revoked(jti: str) -> bool:
        return db.session.query(TokenBlocklist.id).filter_by(jti=jti).first() is not None
