"""
Unit tests for structured logging utility.
Tests JSON formatter, timezone handling (Asia/Seoul), log levels.

These tests MUST FAIL initially (TDD approach) until src/utils/logging.py is implemented.
"""

import pytest
import logging
import json
from datetime import datetime
import pytz


def test_json_formatter_creates_structured_logs():
    """Test that logs are formatted as JSON with required fields."""
    from src.utils.logging import setup_logging, JsonFormatter
    import io

    # Create string buffer to capture logs
    log_buffer = io.StringIO()
    handler = logging.StreamHandler(log_buffer)
    handler.setFormatter(JsonFormatter())

    logger = logging.getLogger("test_logger")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)

    # Log a test message
    logger.info("Test message", extra={"stock_code": "005930", "price": 60000})

    # Parse JSON output
    log_output = log_buffer.getvalue()
    log_json = json.loads(log_output.strip())

    # Verify JSON structure
    assert "timestamp" in log_json
    assert "level" in log_json
    assert "message" in log_json
    assert log_json["message"] == "Test message"
    assert log_json["level"] == "INFO"

    # Verify extra fields
    assert "stock_code" in log_json
    assert log_json["stock_code"] == "005930"
    assert "price" in log_json
    assert log_json["price"] == 60000


def test_timezone_is_asia_seoul():
    """Test that timestamps use Asia/Seoul timezone (KST)."""
    from src.utils.logging import JsonFormatter
    import io

    log_buffer = io.StringIO()
    handler = logging.StreamHandler(log_buffer)
    handler.setFormatter(JsonFormatter())

    logger = logging.getLogger("test_tz")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)

    logger.info("Timezone test")

    log_output = log_buffer.getvalue()
    log_json = json.loads(log_output.strip())

    # Verify timestamp contains timezone info
    timestamp_str = log_json["timestamp"]
    assert "+09:00" in timestamp_str or "KST" in timestamp_str  # Asia/Seoul is UTC+9


def test_setup_logging_configures_handlers():
    """Test that setup_logging() configures both file and console handlers."""
    from src.utils.logging import setup_logging
    import tempfile
    import os

    # Create temporary log file
    temp_dir = tempfile.mkdtemp()
    log_file = os.path.join(temp_dir, "test.log")

    try:
        logger = setup_logging(log_file=log_file, level=logging.DEBUG)

        # Verify logger has handlers
        assert len(logger.handlers) >= 1  # At least one handler

        # Log a message
        logger.info("Test log message")

        # Verify file was created and contains log
        assert os.path.exists(log_file)
        with open(log_file, 'r') as f:
            content = f.read()
            assert "Test log message" in content

    finally:
        # Cleanup
        if os.path.exists(log_file):
            os.unlink(log_file)
        os.rmdir(temp_dir)


def test_log_levels_work_correctly():
    """Test that different log levels are handled correctly."""
    from src.utils.logging import JsonFormatter
    import io

    log_buffer = io.StringIO()
    handler = logging.StreamHandler(log_buffer)
    handler.setFormatter(JsonFormatter())

    logger = logging.getLogger("test_levels")
    logger.handlers = [handler]
    logger.setLevel(logging.DEBUG)

    # Log at different levels
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    # Parse all log lines
    log_lines = log_buffer.getvalue().strip().split('\n')
    assert len(log_lines) == 4

    levels = [json.loads(line)["level"] for line in log_lines]
    assert levels == ["DEBUG", "INFO", "WARNING", "ERROR"]


def test_exception_logging_includes_traceback():
    """Test that exceptions are logged with traceback information."""
    from src.utils.logging import JsonFormatter
    import io

    log_buffer = io.StringIO()
    handler = logging.StreamHandler(log_buffer)
    handler.setFormatter(JsonFormatter())

    logger = logging.getLogger("test_exception")
    logger.handlers = [handler]
    logger.setLevel(logging.ERROR)

    try:
        raise ValueError("Test exception")
    except ValueError:
        logger.exception("An error occurred")

    log_output = log_buffer.getvalue()
    log_json = json.loads(log_output.strip())

    assert "exception" in log_json or "traceback" in log_json or "exc_info" in log_json
    assert "ValueError" in str(log_json)
