"""
Bollinger Band indicator calculation (data-model.md Entity 5).
Implements SMA-based bands with squeeze detection integration.
"""


import pandas as pd


def calculate_bollinger_bands(
    close_prices: pd.Series,
    period: int,
    std_multiplier: float
) -> pd.DataFrame:
    """
    Calculate Bollinger Bands from closing prices.

    Args:
        close_prices: Series of closing prices (index should be dates)
        period: Moving average window (e.g., 20)
        std_multiplier: Standard deviation multiplier (e.g., 2.0)

    Returns:
        DataFrame with columns: upper, middle, lower, bandwidth

    Raises:
        ValueError: If period < 2 or std_multiplier <= 0
    """
    # Validation
    if period < 2:
        raise ValueError(f"period must be >= 2, got: {period}")

    if std_multiplier <= 0:
        raise ValueError(f"std_multiplier must be positive, got: {std_multiplier}")

    # Calculate middle band (Simple Moving Average)
    middle = close_prices.rolling(window=period).mean()

    # Calculate standard deviation
    std = close_prices.rolling(window=period).std()

    # Calculate upper and lower bands
    upper = middle + (std * std_multiplier)
    lower = middle - (std * std_multiplier)

    # Calculate bandwidth
    bandwidth = (upper - lower) / middle

    # Create result DataFrame
    result = pd.DataFrame({
        'upper': upper,
        'middle': middle,
        'lower': lower,
        'bandwidth': bandwidth
    }, index=close_prices.index)

    return result
