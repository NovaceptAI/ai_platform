import os

bind = "0.0.0.0:8000"
workers = 4

# Default to stdout/stderr to avoid filesystem issues; allow override via env
accesslog = os.getenv("GUNICORN_ACCESSLOG", "-")
errorlog = os.getenv("GUNICORN_ERRORLOG", "-")
loglevel = os.getenv("GUNICORN_LOGLEVEL", "info")

timeout = 120  # Timeout limit of 2 minutes
reload = True  # Enable automatic reload on code changes