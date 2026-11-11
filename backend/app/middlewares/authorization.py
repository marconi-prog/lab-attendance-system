"""Autorização por perfil."""
from __future__ import annotations

from functools import wraps

from flask_jwt_extended import current_user, verify_jwt_in_request

from app.models import UserRole
from app.utils.errors import PermissionDenied


def roles_required(*roles: UserRole, refresh: bool = False):
    """Exige JWT válido e, se informado, um dos perfis.

    O perfil é lido do banco (current_user), não do token: uma alteração de
    perfil ou desativação vale imediatamente.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request(refresh=refresh)
            if roles and current_user.role not in roles:
                raise PermissionDenied("Você não tem permissão para acessar este recurso.")
            return fn(*args, **kwargs)

        return wrapper

    return decorator
