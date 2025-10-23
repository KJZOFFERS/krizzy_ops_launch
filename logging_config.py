"""
Logging configuration for KRIZZY OPS v3.0.0
"""
import os
import logging
import logging.handlers
from datetime import datetime
from typing import Optional


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up comprehensive logging for KRIZZY OPS.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
    
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("krizzy_ops")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Error file handler
    error_handler = logging.handlers.RotatingFileHandler(
        "logs/errors.log",
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    return logger


def get_logger(name: str = "krizzy_ops") -> logging.Logger:
    """Get logger instance."""
    return logging.getLogger(name)


class KRIZZYOpsLogger:
    """Custom logger wrapper for KRIZZY OPS with structured logging."""
    
    def __init__(self, name: str = "krizzy_ops"):
        self.logger = get_logger(name)
        self.start_time = datetime.now()
    
    def log_boot(self, version: str, environment: str = "production"):
        """Log system boot."""
        self.logger.info(f"KRIZZY OPS v{version} starting in {environment} mode")
        self.logger.info(f"Boot time: {self.start_time.isoformat()}")
    
    def log_cycle_start(self, engine: str, details: dict = None):
        """Log cycle start."""
        details_str = f" - {details}" if details else ""
        self.logger.info(f"Cycle started: {engine}{details_str}")
    
    def log_cycle_end(self, engine: str, count: int, details: dict = None):
        """Log cycle completion."""
        details_str = f" - {details}" if details else ""
        self.logger.info(f"Cycle completed: {engine} - {count} records processed{details_str}")
    
    def log_error(self, error_type: str, message: str, context: dict = None):
        """Log error with context."""
        context_str = f" - Context: {context}" if context else ""
        self.logger.error(f"ERROR [{error_type}]: {message}{context_str}")
    
    def log_warning(self, message: str, context: dict = None):
        """Log warning with context."""
        context_str = f" - Context: {context}" if context else ""
        self.logger.warning(f"WARNING: {message}{context_str}")
    
    def log_info(self, message: str, context: dict = None):
        """Log info with context."""
        context_str = f" - Context: {context}" if context else ""
        self.logger.info(f"INFO: {message}{context_str}")
    
    def log_performance(self, operation: str, duration: float, details: dict = None):
        """Log performance metrics."""
        details_str = f" - {details}" if details else ""
        self.logger.info(f"PERFORMANCE: {operation} took {duration:.2f}s{details_str}")


# Global logger instance
logger = KRIZZYOpsLogger()


def setup_production_logging():
    """Set up production logging configuration."""
    return setup_logging(
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("LOG_FILE", "logs/krizzy_ops.log")
    )


def setup_development_logging():
    """Set up development logging configuration."""
    return setup_logging(
        log_level="DEBUG",
        log_file="logs/krizzy_ops_dev.log"
    )