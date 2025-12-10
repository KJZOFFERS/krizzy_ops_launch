import logging
import sys
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)


def get_logger(name: str) -> logging.Logger:
    """Get logger instance for module"""
    return logging.getLogger(name)


def log_engine_cycle(
    logger: logging.Logger,
    engine_name: str,
    processed: int,
    errors: int,
    duration_seconds: float
):
    """Standard log format for engine cycles"""
    logger.info(
        f"{engine_name} cycle complete: "
        f"processed={processed}, errors={errors}, duration={duration_seconds:.2f}s"
    )


def log_error(logger: logging.Logger, context: str, error: Exception):
    """Standard error logging"""
    logger.error(f"{context}: {type(error).__name__}: {error}", exc_info=True)
