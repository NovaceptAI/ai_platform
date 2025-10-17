from celery import Celery
import os
from urllib.parse import urlparse

def _resolve_url(env_name: str, default: str) -> str:
    """Read a URL from env and ensure it has a hostname."""
    url = os.getenv(env_name) or default
    parsed = urlparse(url)
    if not parsed.scheme:
        raise ValueError(f"{env_name} missing scheme (got: {url!r})")
    # Kombu's 'No hostname supplied' happens when netloc is empty (e.g., redis:///0)
    if not parsed.hostname:
        raise ValueError(f"{env_name} missing hostname (got: {url!r})")
    return url

def make_celery(app):
    """
    Create a Celery instance bound to the Flask app context.
    Reads CELERY_BROKER_URL and CELERY_RESULT_BACKEND. Falls back to sane defaults.
    """
    # Defaults:
    # - Local Redis without auth
    # - Separate DBs to avoid key collisions
    default_broker  = "redis://127.0.0.1:6379/0"
    default_backend = "redis://127.0.0.1:6379/1"

    # Allow REDIS_URL for backward compatibility if both standard vars are absent
    compat = os.getenv("REDIS_URL")
    broker_url  = os.getenv("CELERY_BROKER_URL") or (compat if compat else default_broker)
    backend_url = os.getenv("CELERY_RESULT_BACKEND") or (compat.replace("/0", "/1") if compat else default_backend)

    # Validate
    broker_url  = _resolve_url("CELERY_BROKER_URL/REDIS_URL(broker)", broker_url)
    backend_url = _resolve_url("CELERY_RESULT_BACKEND/REDIS_URL(backend)", backend_url)

    celery = Celery(app.import_name, broker=broker_url, backend=backend_url)

    # Hardening & sane timeouts (tweak as needed)
    celery.conf.update(
        broker_url=broker_url,
        result_backend=backend_url,
        broker_connection_retry_on_startup=True,
        broker_heartbeat=30,
        broker_pool_limit=10,
        broker_transport_options={
            "visibility_timeout": 3600,    # 1h
            "socket_timeout": 5,
            "retry_on_timeout": True,
        },
        redis_backend_use_ssl=backend_url.startswith("rediss://") or None,
        redis_max_connections=50,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_hijack_root_logger=False,
        worker_redirect_stdouts=True,
        worker_redirect_stdouts_level="INFO",
    )

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask

    # Helpful startup print (shows exactly what the API is using)
    app.logger.info(f"[Celery] broker_url={celery.conf.broker_url}")
    app.logger.info(f"[Celery] result_backend={celery.conf.result_backend}")

    return celery
