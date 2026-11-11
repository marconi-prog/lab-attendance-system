"""Factory da aplicação Flask."""
from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

load_dotenv()

from app.config import get_config, validate_config  # noqa: E402
from app.extensions import cors, db, jwt, migrate, socketio  # noqa: E402


def _configure_logging(level: str) -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("engineio").setLevel(logging.WARNING)
    logging.getLogger("socketio").setLevel(logging.WARNING)


def create_app(config_name: str | None = None, overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))
    if overrides:
        app.config.update(overrides)
    validate_config(app.config)
    app.json.ensure_ascii = False
    app.json.sort_keys = False
    _configure_logging(app.config["LOG_LEVEL"])

    from app import models  # noqa: F401  (registra os modelos no metadata)

    db.init_app(app)
    migrate.init_app(app, db, directory=str(Path(__file__).resolve().parent.parent / "migrations"))
    jwt.init_app(app)
    origins = app.config["CORS_ORIGINS"]
    cors.init_app(app, resources={r"/api/*": {"origins": origins}}, supports_credentials=False)
    socketio.init_app(app, cors_allowed_origins=origins, async_mode="threading", logger=False, engineio_logger=False)

    from app.cli import register_cli
    from app.middlewares import register_error_handlers, register_jwt_callbacks, register_request_hooks
    from app.routes import register_routes
    from app.sockets import register_socket_namespaces

    register_jwt_callbacks(app)
    register_error_handlers(app)
    register_request_hooks(app)
    register_routes(app)
    register_socket_namespaces()
    register_cli(app)
    return app
