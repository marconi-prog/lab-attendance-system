from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import UserRole
from app.schemas.common import Email, LocalDateTime, OutModel, PaginationQuery, StrictModel


def validate_password_strength(value: str) -> str:
    if len(value) < 8:
        raise ValueError("A senha deve ter pelo menos 8 caracteres")
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("A senha deve conter letras e números")
    return value


class CounterBrief(OutModel):
    id: int
    name: str
    number: int


class UserOut(OutModel):
    id: int
    name: str
    email: str
    role: UserRole
    active: bool
    counters: list[CounterBrief] = []
    created_at: LocalDateTime
    updated_at: LocalDateTime


class UserCreate(StrictModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"name": "Ana Souza", "email": "ana@laboratorio.com.br", "password": "Senha1234", "role": "ATTENDANT", "counter_ids": [1, 2]}]})

    name: str = Field(min_length=2, max_length=120)
    email: Email
    password: str = Field(max_length=128)
    role: UserRole
    counter_ids: list[int] = Field(default_factory=list, max_length=50)

    _pw = field_validator("password")(validate_password_strength)


class UserUpdate(StrictModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"name": "Ana Souza Lima", "active": True}]})

    name: str | None = Field(None, min_length=2, max_length=120)
    email: Email | None = None
    role: UserRole | None = None
    active: bool | None = None
    password: str | None = Field(None, max_length=128)

    @field_validator("password")
    @classmethod
    def _pw(cls, value: str | None) -> str | None:
        return validate_password_strength(value) if value is not None else None


class AssignCountersRequest(StrictModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"counter_ids": [1, 3]}]})

    counter_ids: list[int] = Field(max_length=50)


class UserListQuery(PaginationQuery):
    model_config = ConfigDict(extra="ignore")

    search: str | None = Field(None, max_length=120)
    role: UserRole | None = None
    active: bool | None = None


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
