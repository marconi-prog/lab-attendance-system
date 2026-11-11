"""Tarefa periódica em segundo plano: encerramento automático do expediente."""
from __future__ import annotations

import logging

from flask import Flask

from app.extensions import db, socketio

logger = logging.getLogger(__name__)
_started = False


def start_scheduler(app: Flask) -> None:
    global _started
    if _started or not app.config.get("SCHEDULER_ENABLED"):
        return
    _started = True
    interval = app.config["SCHEDULER_INTERVAL_SECONDS"]

    def loop() -> None:
        from app.services.day_closing_service import DayClosingService

        while True:
            with app.app_context():
                try:
                    DayClosingService.run_scheduled()
                except Exception:
                    logger.exception("Falha na rotina de encerramento do expediente")
                finally:
                    db.session.remove()
            socketio.sleep(interval)

    socketio.start_background_task(loop)
    logger.info("Agendador iniciado (intervalo %ss)", interval)
