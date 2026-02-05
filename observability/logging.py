"""Structured logging with Cloud Logging."""

import logging
import structlog
from google.cloud import logging as cloud_logging

from shared.config import get_settings


def init_logging():
    """Initialize structured logging."""
    settings = get_settings()

    # Set up Cloud Logging
    if settings.environment == "production":
        client = cloud_logging.Client()
        client.setup_logging()

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Set log level
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(message)s",
    )


def get_logger(name: str):
    """Get structured logger."""
    return structlog.get_logger(name)
