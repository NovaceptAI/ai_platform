# app/celery_worker.py
from app.main import celery_app  # Uses the already-initialized celery from Flask context
app = celery_app  # Optional: for CLI command