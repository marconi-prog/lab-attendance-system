"""Namespaces Socket.IO.

/panel — público e somente leitura. O cliente apenas recebe eventos;
         o único evento aceito é "panel:sync", que devolve o estado atual.
/staff — exige access token JWT válido em `auth.token` no handshake.
         Usuário desativado ou token revogado tem a conexão recusada.

Nenhum evento enviado por clientes altera o estado do sistema: mudanças
só ocorrem via API REST autenticada; o servidor é a única origem dos
eventos de chamada. A origem (Origin) do handshake é validada pela lista
CORS_ORIGINS configurada em create_app.
"""
from __future__ import annotations

import logging

from flask import request
from flask_jwt_extended import decode_token
from flask_socketio import ConnectionRefusedError, Namespace, emit

from app.extensions import db, socketio
from app.repositories import UserRepository
from app.services.auth_service import AuthService
from app.services.realtime import PANEL_NS, STAFF_NS, Events

logger = logging.getLogger(__name__)


class PanelNamespace(Namespace):
    def on_connect(self, auth=None):
        from app.services.panel_service import PanelService

        try:
            emit(Events.PANEL_UPDATED, PanelService.snapshot())
        finally:
            db.session.remove()

    def on_sync(self, _data=None):
        from app.services.panel_service import PanelService

        try:
            return PanelService.snapshot()
        finally:
            db.session.remove()


class StaffNamespace(Namespace):
    def on_connect(self, auth=None):
        token = (auth or {}).get("token") if isinstance(auth, dict) else None
        if not token:
            raise ConnectionRefusedError("unauthorized")
        try:
            payload = decode_token(token)
            if payload.get("type") != "access" or AuthService.is_token_revoked(payload["jti"]):
                raise ConnectionRefusedError("unauthorized")
            user = UserRepository.get(int(payload["sub"]))
            if not user or not user.active:
                raise ConnectionRefusedError("unauthorized")
            logger.info("Socket /staff conectado: user_id=%s sid=%s", user.id, request.sid)
        except ConnectionRefusedError:
            raise
        except Exception:
            raise ConnectionRefusedError("unauthorized")
        finally:
            db.session.remove()


def register_socket_namespaces() -> None:
    socketio.on_namespace(PanelNamespace(PANEL_NS))
    socketio.on_namespace(StaffNamespace(STAFF_NS))
