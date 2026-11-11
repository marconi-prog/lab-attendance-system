from __future__ import annotations

from flask_jwt_extended import current_user, get_jwt

from app.schemas.auth import AccessTokenOut, ChangePasswordRequest, LoginRequest, LogoutRequest, TokenPairOut
from app.schemas.user import UserOut
from app.services.auth_service import AuthService


def login(body: LoginRequest):
    user, access, refresh = AuthService.login(body.email, body.password)
    return TokenPairOut(access_token=access, refresh_token=refresh, user=UserOut.model_validate(user))


def refresh():
    return AccessTokenOut(access_token=AuthService.refresh(current_user))


def logout(body: LogoutRequest):
    AuthService.logout(current_user, get_jwt(), body.refresh_token)
    return None


def me():
    return UserOut.model_validate(current_user)


def change_password(body: ChangePasswordRequest):
    AuthService.change_password(current_user, body.current_password, body.new_password)
    return None
