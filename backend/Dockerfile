FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_APP=app:create_app

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN useradd --create-home --uid 10001 appuser && chmod +x docker-entrypoint.sh
USER appuser

EXPOSE 5000
ENTRYPOINT ["./docker-entrypoint.sh"]
# Um único worker com threads: o Flask-SocketIO mantém as conexões em memória.
CMD ["gunicorn", "-w", "1", "--threads", "64", "-b", "0.0.0.0:5000", "--timeout", "120", "--access-logfile", "-", "wsgi:app"]
