"""Servidor de desenvolvimento: python run.py"""
import os

from app import create_app
from app.extensions import socketio
from app.scheduler import start_scheduler

app = create_app()

if __name__ == "__main__":
    start_scheduler(app)
    socketio.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "5000")),
        debug=app.config["DEBUG"],
        use_reloader=False,
        allow_unsafe_werkzeug=True,
    )
