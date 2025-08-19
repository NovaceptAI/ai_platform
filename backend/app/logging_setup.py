import logging
import os
import sys
from logging.handlers import RotatingFileHandler


def _parse_bool(value: str) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def configure_logging(app=None) -> None:
    """Configure application-wide logging once.

    - Defaults to logging to stdout
    - Optional rotating file logging when LOG_TO_FILE=1
    - Honors LOG_LEVEL, LOG_DIR, LOG_FILE env vars
    - Makes Flask's app.logger propagate to root
    """

    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    log_to_file = _parse_bool(os.getenv("LOG_TO_FILE"))
    log_dir = os.getenv("LOG_DIR", os.path.join(os.path.dirname(__file__), "logs"))
    log_file_name = os.getenv("LOG_FILE", "app.log")

    log_format = (
        "%(asctime)s %(levelname)s [%(name)s] %(message)s "
        "[in %(pathname)s:%(lineno)d]"
    )
    formatter = logging.Formatter(log_format)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Ensure we have exactly one stdout handler
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(log_level)
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)

    # Optional rotating file handler
    if log_to_file:
        os.makedirs(log_dir, exist_ok=True)
        file_path = os.path.join(log_dir, log_file_name)
        already_added = False
        for h in root_logger.handlers:
            if isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", None) == file_path:
                already_added = True
                break
        if not already_added:
            file_handler = RotatingFileHandler(
                file_path,
                maxBytes=10_000_000,
                backupCount=5,
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

    # Make Flask app logger propagate and avoid duplicate handlers
    if app is not None:
        # Clear handlers attached by Flask default to avoid duplicate output
        app.logger.handlers.clear()
        app.logger.setLevel(log_level)
        app.logger.propagate = True

