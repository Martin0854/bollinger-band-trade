"""
Unit tests for Bollinger Band calculation (data-model.md Entity 4).
Tests middle=SMA, upper/lower=middle±(std*multiplier), band ordering invariants.
Compares against pandas-ta reference implementation.

These tests MUST FAIL initially (TDD) until src/indicators/bollinger.py is implemented.
"""

import pytest
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime, timedelta


def test_bollinger_bands_calculation_basic():
    """Test Bollinger Bands calculation with simple data."""
    from src.indicators.bollinger import calculate_bollinger_bands

    # Create simple price data
    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    close_prices = pd.Series([60000] * 30, index=dates)

    result = calculate_bollinger_bands(
        close_prices=close_prices,
        period=20,
        std_multiplier=2.0
    )

    # With constant prices:
    # - Middle band should equal price (SMA of constants = constant)
    # - Standard deviation = 0, so upper = lower = middle
    assert result['middle'].iloc[-1] == pytest.approx(60000, rel=1e-6)
    assert result['upper'].iloc[-1] == pytest.approx(60000, rel=1e-6)
    assert result['lower'].iloc[-1] == pytest.approx(60000, rel=1e-6)
    assert result['bandwidth'].iloc[-1] == pytest.approx(0, abs=1e-6)


def test_bollinger_bands_with_volatility():
    """Test Bollinger Bands with volatile price data."""
    from src.indicators.bollinger import calculate_bollinger_bands

    # Create volatile price series
    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    prices = [60000, 61000, 59000, 62000, 58000, 63000, 57000, 64000, 56000, 65000,
              60000, 61000, 59000, 62000, 58000, 63000, 57000, 64000, 56000, 65000,
              60000, 61000, 59000, 62000, 58000, 63000, 57000, 64000, 56000, 65000]
    close_prices = pd.Series(prices, index=dates)

    result = calculate_bollinger_bands(
        close_prices=close_prices,
        period=20,
        std_multiplier=2.0
    )

    # Verify band ordering: lower <= middle <= upper (filter out NaN rows)
    valid_rows = result['middle'].notna()
    assert (result.loc[valid_rows, 'lower'] <= result.loc[valid_rows, 'middle']).all()
    assert (result.loc[valid_rows, 'middle'] <= result.loc[valid_rows, 'upper']).all()

    # Verify bandwidth > 0 for volatile data
    assert result['bandwidth'].iloc[-1] > 0


def test_bollinger_bands_middle_equals_sma():
    """Test middle band equals Simple Moving Average."""
    from src.indicators.bollinger import calculate_bollinger_bands

    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    prices = np.random.randint(55000, 65000, size=30)
    close_prices = pd.Series(prices, index=dates)

    result = calculate_bollinger_bands(
        close_prices=close_prices,
        period=20,
        std_multiplier=2.0
    )

    # Manual SMA calculation for verification
    sma_manual = close_prices.rolling(window=20).mean()

    # Middle band should equal SMA
    pd.testing.assert_series_equal(
        result['middle'],
        sma_manual,
        check_names=False,
        rtol=1e-6
    )


def test_bollinger_bands_formula_verification():
    """Test upper/lower = middle ± (std * multiplier)."""
    from src.indicators.bollinger import calculate_bollinger_bands

    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    prices = np.random.randint(55000, 65000, size=30)
    close_prices = pd.Series(prices, index=dates)

    period = 20
    multiplier = 2.0

    result = calculate_bollinger_bands(
        close_prices=close_prices,
        period=period,
        std_multiplier=multiplier
    )

    # Manual calculation
    sma = close_prices.rolling(window=period).mean()
    std = close_prices.rolling(window=period).std()

    expected_upper = sma + (std * multiplier)
    expected_lower = sma - (std * multiplier)

    pd.testing.assert_series_equal(
        result['upper'],
        expected_upper,
        check_names=False,
        rtol=1e-6
    )

    pd.testing.assert_series_equal(
        result['lower'],
        expected_lower,
        check_names=False,
        rtol=1e-6
    )


def test_bollinger_bands_bandwidth_calculation():
    """Test bandwidth = (upper - lower) / middle."""
    from src.indicators.bollinger import calculate_bollinger_bands

    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    prices = np.random.randint(55000, 65000, size=30)
    close_prices = pd.Series(prices, index=dates)

    result = calculate_bollinger_bands(
        close_prices=close_prices,
        period=20,
        std_multiplier=2.0
    )

    # Verify bandwidth formula
    expected_bandwidth = (result['upper'] - result['lower']) / result['middle']

    pd.testing.assert_series_equal(
        result['bandwidth'],
        expected_bandwidth,
        check_names=False,
        rtol=1e-6
    )


@pytest.mark.skip(reason="pandas_ta not in minimal dependencies - optional validation")
def test_bollinger_bands_against_pandas_ta():
    """Test our implementation matches pandas-ta reference."""
    from src.indicators.bollinger import calculate_bollinger_bands
    import pandas_ta as ta

    dates = pd.date_range('2024-01-01', periods=50, freq='D')
    prices = np.random.randint(55000, 65000, size=50)
    close_prices = pd.Series(prices, index=dates)

    # Our implementation
    our_result = calculate_bollinger_bands(
        close_prices=close_prices,
        period=20,
        std_multiplier=2.0
    )

    # pandas-ta reference
    bbands = ta.bbands(close_prices, length=20, std=2.0)

    # Compare (drop NaN rows from beginning)
    valid_idx = our_result['middle'].notna()

    pd.testing.assert_series_equal(
        our_result['middle'][valid_idx],
        bbands['BBM_20_2.0'][valid_idx],
        check_names=False,
        rtol=1e-5
    )

    pd.testing.assert_series_equal(
        our_result['upper'][valid_idx],
        bbands['BBU_20_2.0'][valid_idx],
        check_names=False,
        rtol=1e-5
    )

    pd.testing.assert_series_equal(
        our_result['lower'][valid_idx],
        bbands['BBL_20_2.0'][valid_idx],
        check_names=False,
        rtol=1e-5
    )


def test_bollinger_bands_period_validation():
    """Test period must be >= 2."""
    from src.indicators.bollinger import calculate_bollinger_bands

    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    close_prices = pd.Series([60000] * 30, index=dates)

    with pytest.raises(ValueError, match="period"):
        calculate_bollinger_bands(
            close_prices=close_prices,
            period=1,  # Invalid: too small
            std_multiplier=2.0
        )


def test_bollinger_bands_std_multiplier_validation():
    """Test std_multiplier must be positive."""
    from src.indicators.bollinger import calculate_bollinger_bands

    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    close_prices = pd.Series([60000] * 30, index=dates)

    with pytest.raises(ValueError, match="std_multiplier"):
        calculate_bollinger_bands(
            close_prices=close_prices,
            period=20,
            std_multiplier=0  # Invalid: must be positive
        )


def test_bollinger_bands_insufficient_data():
    """Test handling when data length < period."""
    from src.indicators.bollinger import calculate_bollinger_bands

    dates = pd.date_range('2024-01-01', periods=10, freq='D')
    close_prices = pd.Series([60000] * 10, index=dates)

    # Should not raise, but result should have NaN for early rows
    result = calculate_bollinger_bands(
        close_prices=close_prices,
        period=20,
        std_multiplier=2.0
    )

    # All values should be NaN since we don't have enough data
    assert result['middle'].isna().all()
    assert result['upper'].isna().all()
    assert result['lower'].isna().all()


def test_bollinger_bands_return_structure():
    """Test function returns DataFrame with expected columns."""
    from src.indicators.bollinger import calculate_bollinger_bands

    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    close_prices = pd.Series([60000] * 30, index=dates)

    result = calculate_bollinger_bands(
        close_prices=close_prices,
        period=20,
        std_multiplier=2.0
    )

    # Verify structure
    assert isinstance(result, pd.DataFrame)
    assert 'upper' in result.columns
    assert 'middle' in result.columns
    assert 'lower' in result.columns
    assert 'bandwidth' in result.columns
    assert len(result) == len(close_prices)
