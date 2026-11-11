"""Publicação de eventos Socket.IO.

Eventos são emitidos SOMENTE pelo servidor e SOMENTE após o commit da
transação — o painel nunca exibe uma senha que não foi efetivamente chamada.

Namespaces:
  /panel  público, somente leitura (painel de TV)
  /staff  exige JWT válido (atendentes e gestores)
"""
from __future__ import annotations

import logging
from typing import Any

from app.extensions import socketio

PANEL_NS = "/panel"
STAFF_NS = "/staff"

logger = logging.getLogger(__name__)


class Events:
    TICKET_ISSUED = "ticket:issued"
    TICKET_CALLED = "ticket:called"
    TICKET_RECALLED = "ticket:recalled"
    TICKET_UPDATED = "ticket:updated"
    ATTENDANCE_STARTED = "attendance:started"
    ATTENDANCE_FINISHED = "attendance:finished"
    PANEL_UPDATED = "panel:updated"
    QUEUE_UPDATED = "queue:updated"


class RealtimeNotifier:
    @staticmethod
    def _emit(event: str, payload: Any, namespace: str) -> None:
        try:
            socketio.emit(event, payload, namespace=namespace)
        except Exception:  # falha de broadcast não pode desfazer uma operação já confirmada
            logger.exception("Falha ao emitir evento %s em %s", event, namespace)

    @classmethod
    def to_panel(cls, event: str, payload: Any) -> None:
        cls._emit(event, payload, PANEL_NS)

    @classmethod
    def to_staff(cls, event: str, payload: Any) -> None:
        cls._emit(event, payload, STAFF_NS)

    @classmethod
    def broadcast(cls, event: str, payload: Any) -> None:
        cls.to_panel(event, payload)
        cls.to_staff(event, payload)
