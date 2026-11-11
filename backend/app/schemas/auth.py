from __future__ import annotations

from pydantic import ConfigDict, Field

from app.schemas.common import Email, OutModel, StrictModel
from app.schemas.user import UserOut


class LoginRequest(StrictModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"email": "atendente@laboratorio.com.br", "password": "SuaSenha123"}]})

    email: Email
    password: str = Field(min_length=1, max_length=128)


class LogoutRequest(StrictModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"refresh_token": "eyJhbGciOiJIUzI1NiIs..."}]})

    refresh_token: str | None = Field(None, max_length=2048)


class ChangePasswordRequest(StrictModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"current_password": "SenhaAtual1", "new_password": "NovaSenha123"}]})

    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class TokenPairOut(OutModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    user: UserOut


class AccessTokenOut(OutModel):
    access_token: str
    token_type: str = "Bearer"
