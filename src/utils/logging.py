"""
Structured logging utility with JSON formatter and Asia/Seoul timezone.
Implements plan.md Principle V: Transparency & Auditability
"""

import logging
import json
from datetime import datetime
import pytz
from typing import Optional


class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    All logs formatted as JSON with timezone-aware timestamps (Asia/Seoul).
    """

    def __init__(self):
        super().__init__()
        self.tz = pytz.timezone('Asia/Seoul')

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON string.

        Args:
            record: Python logging record

        Returns:
            JSON-formatted log string
        """
        # Create base log structure
        log_data = {
            "timestamp": datetime.now(self.tz).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if provided
        if hasattr(record, 'stock_code'):
            log_data['stock_code'] = record.stock_code
        if hasattr(record, 'price'):
            log_data['price'] = record.price
        if hasattr(record, 'quantity'):
            log_data['quantity'] = record.quantity
        if hasattr(record, 'action'):
            log_data['action'] = record.action
        if hasattr(record, 'reason'):
            log_data['reason'] = record.reason

        # Copy all extra fields from record.__dict__
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                           'levelname', 'levelno', 'lineno', 'module', 'msecs',
                           'pathname', 'process', 'processName', 'relativeCreated',
                           'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info']:
                if key not in log_data:
                    log_data[key] = value

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


def setup_logging(
    log_file: Optional[str] = None,
    level: int = logging.INFO,
    console: bool = True
) -> logging.Logger:
    """
    Setup structured logging with JSON formatter and Asia/Seoul timezone.

    Args:
        log_file: Path to log file (optional, logs to console only if None)
        level: Logging level (default: INFO)
        console: Whether to log to console (default: True)

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger('bollinger_band_trade')
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers = []

    # Create JSON formatter
    formatter = JsonFormatter()

    # Console handler
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str = 'bollinger_band_trade') -> logging.Logger:
    """
    Get existing logger instance.

    Args:
        name: Logger name (default: 'bollinger_band_trade')

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
