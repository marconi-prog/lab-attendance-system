"""Relógio da aplicação.

Datas são persistidas em UTC (DATETIME sem fuso). As regras de negócio
(expediente, sequência diária, relatórios) usam o fuso America/Recife.
Os testes substituem `Clock.now_utc` para simular horários.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from flask import current_app, has_app_context

DEFAULT_TZ = "America/Recife"


def _tz() -> ZoneInfo:
    name = current_app.config.get("TIMEZONE", DEFAULT_TZ) if has_app_context() else DEFAULT_TZ
    return ZoneInfo(name)


class Clock:
    @staticmethod
    def now_utc() -> datetime:
        return datetime.now(timezone.utc)


def utcnow() -> datetime:
    """Instante atual em UTC, sem tzinfo (formato armazenado no MySQL)."""
    return Clock.now_utc().astimezone(timezone.utc).replace(tzinfo=None)


def local_now() -> datetime:
    return Clock.now_utc().astimezone(_tz())


def local_today() -> date:
    return local_now().date()


def to_local(value: datetime | None) -> datetime | None:
    """Converte um datetime UTC sem fuso (vindo do banco) para o fuso local."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(_tz())


def local_day_bounds_utc(day: date) -> tuple[datetime, datetime]:
    """Intervalo [início, fim) de um dia local, expresso em UTC sem fuso."""
    tz = _tz()
    start = datetime.combine(day, time.min, tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)
    return start, end
