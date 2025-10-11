"""
Defensive validation utilities per plan.md Principle VII.
Fail-fast validation with structured error messages.
"""

from typing import List, Tuple
import pandas as pd


class ValidationError(Exception):
    """Custom exception for validation failures."""
    pass


def validate_stock_code(code: str) -> str:
    """
    Validate Korean stock code format (6 digits).

    Args:
        code: Stock code to validate

    Returns:
        Validated stock code

    Raises:
        ValidationError: If code format is invalid
    """
    if not isinstance(code, str):
        raise ValidationError(f"Stock code must be string, got {type(code).__name__}")

    if not (code.isdigit() and len(code) == 6):
        raise ValidationError(
            f"Invalid stock code: '{code}'. "
            f"Korean stock codes must be exactly 6 digits (e.g., '005930')"
        )

    return code


def validate_ohlcv_dataframe(df: pd.DataFrame, stock_code: str) -> None:
    """
    Validate OHLCV DataFrame structure and data integrity.

    Args:
        df: DataFrame with OHLCV data
        stock_code: Stock code for error messages

    Raises:
        ValidationError: If DataFrame structure or data is invalid
    """
    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']

    # Check required columns exist
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValidationError(
            f"Missing required columns for stock {stock_code}: {missing_cols}. "
            f"Expected: {required_cols}"
        )

    # Check DataFrame is not empty
    if len(df) == 0:
        raise ValidationError(f"Empty OHLCV data for stock {stock_code}")

    # Check all values are positive
    if not (df[required_cols] > 0).all().all():
        raise ValidationError(
            f"OHLCV data for stock {stock_code} contains non-positive values. "
            f"All prices and volumes must be > 0"
        )

    # Check OHLC relationships
    if not (df['Low'] <= df['Close']).all():
        invalid_rows = df[df['Low'] > df['Close']]
        raise ValidationError(
            f"OHLCV data for stock {stock_code} violates Low <= Close constraint. "
            f"Found {len(invalid_rows)} invalid rows"
        )

    if not (df['High'] >= df['Close']).all():
        invalid_rows = df[df['High'] < df['Close']]
        raise ValidationError(
            f"OHLCV data for stock {stock_code} violates High >= Close constraint. "
            f"Found {len(invalid_rows)} invalid rows"
        )

    if not (df['Low'] <= df['Open']).all():
        invalid_rows = df[df['Low'] > df['Open']]
        raise ValidationError(
            f"OHLCV data for stock {stock_code} violates Low <= Open constraint. "
            f"Found {len(invalid_rows)} invalid rows"
        )

    if not (df['High'] >= df['Open']).all():
        invalid_rows = df[df['High'] < df['Open']]
        raise ValidationError(
            f"OHLCV data for stock {stock_code} violates High >= Open constraint. "
            f"Found {len(invalid_rows)} invalid rows"
        )


def validate_cash_nonnegative(cash_balance: float, context: str = "") -> None:
    """
    Validate cash balance is non-negative (constitutional requirement).

    Args:
        cash_balance: Cash balance to validate
        context: Optional context for error message

    Raises:
        ValidationError: If cash balance is negative
    """
    if cash_balance < 0:
        msg = f"Cash balance cannot be negative: {cash_balance}"
        if context:
            msg += f" (context: {context})"
        raise ValidationError(msg)


def validate_quantity_positive(quantity: int, stock_code: str = "") -> None:
    """
    Validate position quantity is positive.

    Args:
        quantity: Position quantity
        stock_code: Stock code for error message

    Raises:
        ValidationError: If quantity is not positive
    """
    if quantity <= 0:
        msg = f"Position quantity must be positive, got {quantity}"
        if stock_code:
            msg += f" for stock {stock_code}"
        raise ValidationError(msg)


def validate_price_positive(price: float, label: str = "Price") -> None:
    """
    Validate price is positive.

    Args:
        price: Price to validate
        label: Label for error message (e.g., "Purchase price")

    Raises:
        ValidationError: If price is not positive
    """
    if price <= 0:
        raise ValidationError(f"{label} must be positive, got {price}")


def validate_date_range(start_date, end_date) -> None:
    """
    Validate date range (start < end).

    Args:
        start_date: Start date
        end_date: End date

    Raises:
        ValidationError: If start >= end
    """
    if start_date >= end_date:
        raise ValidationError(
            f"Start date must be before end date: {start_date} >= {end_date}"
        )
