"""
Structured Logging Configuration.
Sets up standardized Python logging format with timestamps, levels, and logger names.
"""

import logging
import sys


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configures application-wide logging with consistent format and handlers."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    log_format = "%(asctime)s | %(levelname)-8s | %(name)-24s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )

    logger = logging.getLogger("aegisops")
    logger.setLevel(log_level)
    return logger
