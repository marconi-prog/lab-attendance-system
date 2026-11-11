"""Cabeçalhos de segurança e log de acesso (sem corpo, sem tokens, sem senhas)."""
from __future__ import annotations

import logging
import time

from flask import Flask, g, request

logger = logging.getLogger("app.access")


def register_request_hooks(app: Flask) -> None:
    @app.before_request
    def _start_timer():
        g.request_started = time.perf_counter()

    @app.after_request
    def _security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")
        if request.path in ("/api/docs", "/api/docs/"):  # só a página HTML; o JSON nunca fica em cache
            response.headers["Cache-Control"] = "public, max-age=300"
        elapsed_ms = (time.perf_counter() - g.get("request_started", time.perf_counter())) * 1000
        if not request.path.startswith("/socket.io"):
            logger.info("%s %s %s %.1fms", request.method, request.path, response.status_code, elapsed_ms)
        return response
