"""
AI Stock Analyzer - Structured Logging
Mengkonfigurasi format log menjadi JSON agar mudah diparsing oleh tools log management seperti ELK atau Datadog.
"""

import logging
import sys

from pythonjsonlogger import jsonlogger

from app.core.config import settings


def setup_logging():
    logger = logging.getLogger()

    # Hapus handler default uvicorn
    for handler in logger.handlers:
        logger.removeHandler(handler)

    log_handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO if not settings.DEBUG else logging.DEBUG)

    # Supress library logs yang berisik
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    return logger
