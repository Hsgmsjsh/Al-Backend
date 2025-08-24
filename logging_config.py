import logging
import sys
from logging.config import dictConfig

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        },
        "detailed": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)-25s | %(funcName)-15s | Line:%(lineno)-4d | %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "detailed",
            "stream": sys.stdout,
        },
    },
    "loggers": {
        "uvicorn": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "telegram_indexer": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "motor": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

def setup_logging():
    dictConfig(LOGGING_CONFIG)
    return logging.getLogger("telegram_indexer")
