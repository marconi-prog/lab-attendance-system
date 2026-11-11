from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any

import re
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, PlainSerializer, model_validator

from app.utils.clock import to_local


def serialize_local(value: datetime | None) -> str | None:
    local = to_local(value)
    return local.isoformat(timespec="seconds") if local else None


# Datetime armazenado em UTC, exposto em ISO 8601 no fuso America/Recife.
LocalDateTime = Annotated[datetime, PlainSerializer(serialize_local, return_type=str)]


_EMAIL_RE = re.compile(r"[a-z0-9._%+\-]+@[a-z0-9\-]+(\.[a-z0-9\-]+)+")


def _validate_email(value: str) -> str:
    # Aceita domínios internos (ex.: laboratorio.local), comuns em intranets.
    value = value.strip().lower()
    if not _EMAIL_RE.fullmatch(value):
        raise ValueError("E-mail inválido")
    return value


Email = Annotated[str, Field(max_length=180), AfterValidator(_validate_email)]


class StrictModel(BaseModel):
    """Base para corpos de requisição: rejeita campos desconhecidos."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OutModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PaginationQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)


class PeriodQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def _check_period(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date deve ser anterior ou igual a end_date")
        if self.start_date and self.end_date and (self.end_date - self.start_date).days > 366:
            raise ValueError("O período máximo é de 366 dias")
        return self


class PageMeta(BaseModel):
    page: int
    per_page: int
    total: int
    pages: int


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
