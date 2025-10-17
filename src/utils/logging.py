"""
Structured logging utility with JSON formatter and Asia/Seoul timezone.
Implements plan.md Principle V: Transparency & Auditability
"""

import json
import logging
from datetime import datetime
from typing import Optional

import pytz


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


# ========================================================================
# Structured Logging Helpers for Indicator Calculations (Phase 8 - T067)
# ========================================================================

def log_indicator_calculation(
    logger: logging.Logger,
    indicator_name: str,
    stock_code: str,
    value: float,
    **kwargs
) -> None:
    """
    Log indicator calculation with structured fields.

    Args:
        logger: Logger instance
        indicator_name: Name of indicator (e.g., "RSI", "MACD", "ATR", "Volume")
        stock_code: Stock code
        value: Calculated indicator value
        **kwargs: Additional fields (e.g., period, threshold, pass_fail)

    Example:
        >>> log_indicator_calculation(
        >>>     logger, "RSI", "005930", 65.5,
        >>>     period=14, overbought=70, pass=True
        >>> )
    """
    extra = {
        'indicator': indicator_name,
        'stock_code': stock_code,
        'value': value,
        **kwargs
    }
    logger.debug(
        f"{indicator_name} calculated: {value:.2f}",
        extra=extra
    )


def log_filter_result(
    logger: logging.Logger,
    filter_name: str,
    stock_code: str,
    passed: bool,
    reason: str = "",
    **kwargs
) -> None:
    """
    Log filter pass/fail result with structured fields.

    Args:
        logger: Logger instance
        filter_name: Name of filter (e.g., "Volume", "RSI", "MACD")
        stock_code: Stock code
        passed: Whether filter passed (True/False)
        reason: Reason for filter result (optional)
        **kwargs: Additional fields (e.g., current_value, threshold)

    Example:
        >>> log_filter_result(
        >>>     logger, "RSI", "005930", False,
        >>>     reason="overbought",
        >>>     rsi_value=75.0, threshold=70
        >>> )
    """
    extra = {
        'filter': filter_name,
        'stock_code': stock_code,
        'passed': passed,
        'reason': reason,
        **kwargs
    }

    if passed:
        logger.debug(
            f"{filter_name} filter passed: {reason}",
            extra=extra
        )
    else:
        logger.info(
            f"{filter_name} filter blocked signal: {reason}",
            extra=extra
        )


def log_confidence_score(
    logger: logging.Logger,
    stock_code: str,
    score: int,
    threshold: int,
    volume_pass: bool,
    rsi_pass: bool,
    macd_pass: bool,
    meets_threshold: bool
) -> None:
    """
    Log confidence score calculation with all filter results.

    Args:
        logger: Logger instance
        stock_code: Stock code
        score: Calculated confidence score (0-100)
        threshold: Minimum threshold for entry
        volume_pass: Volume filter passed
        rsi_pass: RSI filter passed
        macd_pass: MACD filter passed
        meets_threshold: Whether score meets threshold

    Example:
        >>> log_confidence_score(
        >>>     logger, "005930", 75, 60,
        >>>     volume_pass=True, rsi_pass=True, macd_pass=True,
        >>>     meets_threshold=True
        >>> )
    """
    extra = {
        'stock_code': stock_code,
        'confidence_score': score,
        'threshold': threshold,
        'volume_pass': volume_pass,
        'rsi_pass': rsi_pass,
        'macd_pass': macd_pass,
        'meets_threshold': meets_threshold
    }

    if meets_threshold:
        logger.info(
            f"Confidence score passed: {score}/{threshold} "
            f"(volume={volume_pass}, rsi={rsi_pass}, macd={macd_pass})",
            extra=extra
        )
    else:
        logger.info(
            f"Confidence score failed: {score}/{threshold} "
            f"(volume={volume_pass}, rsi={rsi_pass}, macd={macd_pass})",
            extra=extra
        )


def log_atr_stop_loss(
    logger: logging.Logger,
    stock_code: str,
    entry_price: float,
    atr_value: float,
    stop_loss_price: float,
    multiplier: float
) -> None:
    """
    Log ATR-based dynamic stop-loss calculation.

    Args:
        logger: Logger instance
        stock_code: Stock code
        entry_price: Position entry price
        atr_value: Current ATR value
        stop_loss_price: Calculated stop-loss price
        multiplier: ATR multiplier used

    Example:
        >>> log_atr_stop_loss(
        >>>     logger, "005930", 60000, 2000, 56000, 2.0
        >>> )
    """
    stop_loss_percent = ((entry_price - stop_loss_price) / entry_price) * 100

    extra = {
        'stock_code': stock_code,
        'entry_price': entry_price,
        'atr_value': atr_value,
        'atr_multiplier': multiplier,
        'stop_loss_price': stop_loss_price,
        'stop_loss_percent': round(stop_loss_percent, 2)
    }

    logger.info(
        f"ATR dynamic stop-loss: {stop_loss_price:.2f} "
        f"({stop_loss_percent:.2f}% below entry, ATR={atr_value:.2f}*{multiplier})",
        extra=extra
    )
