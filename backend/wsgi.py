"""Ponto de entrada de produção (Gunicorn).

    gunicorn -w 1 --threads 64 -b 0.0.0.0:5000 wsgi:app

Um único worker: o Flask-SocketIO mantém as conexões em memória. Para
escalar horizontalmente, configure um message_queue (Redis) no SocketIO.
"""
from app import create_app
from app.scheduler import start_scheduler

app = create_app()
start_scheduler(app)
