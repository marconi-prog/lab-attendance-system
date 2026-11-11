"""Configuração da aplicação, carregada de variáveis de ambiente.

Nenhuma credencial possui valor padrão: em produção a aplicação se recusa a
iniciar sem JWT_SECRET_KEY, SECRET_KEY e DATABASE_URL.
"""
from __future__ import annotations

import os
from datetime import time, timedelta


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _time(name: str, default: str) -> time:
    raw = os.getenv(name, default)
    hours, minutes = raw.split(":")
    return time(int(hours), int(minutes))


def _list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


class BaseConfig:
    APP_NAME = "Sistema de Controle de Atendimento"
    APP_VERSION = "1.0.0"
    LAB_NAME = os.getenv("LAB_NAME", "Laboratório de Análises Clínicas")

    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
        # Isolamento READ COMMITTED: leituras com FOR UPDATE enxergam sempre o
        # último valor confirmado, reduzindo gap locks e deadlocks no InnoDB.
        "isolation_level": "READ COMMITTED",
    }

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "30")))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "7")))
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_ERROR_MESSAGE_KEY = "message"

    CORS_ORIGINS = _list("CORS_ORIGINS", "http://localhost:8081,http://localhost:8080")

    TIMEZONE = os.getenv("APP_TIMEZONE", "America/Recife")
    BUSINESS_OPEN_TIME = _time("BUSINESS_OPEN_TIME", "07:00")
    BUSINESS_CLOSE_TIME = _time("BUSINESS_CLOSE_TIME", "17:00")
    TICKET_ISSUE_OPEN_TIME = _time("TICKET_ISSUE_OPEN_TIME", "06:00")
    ENFORCE_BUSINESS_HOURS = _bool("ENFORCE_BUSINESS_HOURS", True)
    MAX_DAILY_SEQUENCE = 999
    MAX_CALL_ATTEMPTS = 2

    SCHEDULER_ENABLED = _bool("SCHEDULER_ENABLED", True)
    SCHEDULER_INTERVAL_SECONDS = int(os.getenv("SCHEDULER_INTERVAL_SECONDS", "60"))

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    TESTING = False
    DEBUG = False


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    pass


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL")
    SECRET_KEY = os.getenv("SECRET_KEY") or "test-only-secret-key-not-for-production-use"
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or "test-only-jwt-secret-key-not-for-production-use"
    SCHEDULER_ENABLED = False
    ENFORCE_BUSINESS_HOURS = True
    LOG_LEVEL = "WARNING"


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config(name: str | None = None) -> type[BaseConfig]:
    env = (name or os.getenv("FLASK_ENV") or "development").lower()
    return CONFIG_BY_NAME.get(env, DevelopmentConfig)


def validate_config(config: dict) -> None:
    """Falha cedo quando a configuração obrigatória está ausente ou insegura."""
    missing = [key for key in ("SECRET_KEY", "JWT_SECRET_KEY", "SQLALCHEMY_DATABASE_URI") if not config.get(key)]
    if missing:
        raise RuntimeError(f"Configuração obrigatória ausente: {', '.join(missing)}. Verifique o arquivo .env.")
    uri = config["SQLALCHEMY_DATABASE_URI"]
    if not uri.startswith("mysql"):
        raise RuntimeError("DATABASE_URL deve apontar para um banco MySQL (mysql+pymysql://...).")
    if not config.get("TESTING") and len(config["JWT_SECRET_KEY"]) < 32:
        raise RuntimeError("JWT_SECRET_KEY deve ter pelo menos 32 caracteres.")
