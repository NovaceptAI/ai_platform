from flask import Flask
from celery import Celery
import os

# app/__init__.py
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Cookies & URLs assume https at the edge
app.config.update(
    PREFERRED_URL_SCHEME="https",
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Lax",
    REMEMBER_COOKIE_SECURE=True,
)

def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=os.getenv("REDIS_URL", "redis://172.178.120.199:6379/0"),
        broker=os.getenv("REDIS_URL", "redis://172.178.120.199:6379/0")
    )
    celery.conf.update(app.config)
    # Ensure Celery does not override root logger so our config applies everywhere
    celery.conf.update(
        worker_hijack_root_logger=False,
        worker_redirect_stdouts=True,
        worker_redirect_stdouts_level="INFO",
    )

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery