from __future__ import annotations

from flask import current_app
from sqlalchemy import text

from app.extensions import db
from app.services.panel_service import PanelService
from app.utils.clock import local_now


def health():
    """Verifica a aplicação e a conexão com o MySQL."""
    try:
        db.session.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        db.session.rollback()
        database = "unavailable"
    status = 200 if database == "ok" else 503
    return {
        "status": "ok" if status == 200 else "degraded",
        "database": database,
        "version": current_app.config["APP_VERSION"],
        "time": local_now().isoformat(timespec="seconds"),
    }, status


def panel():
    return PanelService.snapshot()
