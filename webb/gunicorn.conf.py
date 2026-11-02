"""Gunicorn för fornmed.se. Körs bakom nginx på en unix-socket.

Lokalt kan produktionsvägen provas med en TCP-adress:
    WEBB_BIND=127.0.0.1:8425 gunicorn -c gunicorn.conf.py
"""
import os

wsgi_app = "fornmedwebb.wsgi:application"
bind = os.environ.get("WEBB_BIND", "unix:/run/fornmed-webb/fornmed-webb.sock")
# Sidorna är små och läser ur en lokal databas; två processer räcker gott
workers = int(os.environ.get("WEBB_WORKERS", 2))
timeout = 60
accesslog = "-"
errorlog = "-"
