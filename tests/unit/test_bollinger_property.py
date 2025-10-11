"""
Property-based tests for Bollinger Bands using hypothesis.
Tests mathematical invariants that must hold for ANY valid input data.

These tests MUST FAIL initially (TDD) until src/indicators/bollinger.py is implemented.
"""

import pytest
import pandas as pd
import numpy as np
from hypothesis import given, strategies as st, assume, settings
from decimal import Decimal


@given(
    prices=st.lists(
        st.integers(min_value=10000, max_value=100000),
        min_size=25,
        max_size=100
    ),
    period=st.integers(min_value=5, max_value=20),
    std_multiplier=st.floats(min_value=1.0, max_value=3.0)
)
@settings(deadline=None)
def test_bollinger_bands_ordering_invariant(prices, period, std_multiplier):
    """Property: lower <= middle <= upper must ALWAYS hold."""
    from src.indicators.bollinger import calculate_bollinger_bands

    # Create price series
    dates = pd.date_range('2024-01-01', periods=len(prices), freq='D')
    close_prices = pd.Series(prices, index=dates, dtype=float)

    result = calculate_bollinger_bands(
        close_prices=close_prices,
        period=period,
        std_multiplier=std_multiplier
    )

    # Filter out NaN rows (insufficient data at beginning)
    valid_rows = result['middle'].notna()

    if valid_rows.sum() > 0:
        # Invariant: lower <= middle <= upper
        assert (result.loc[valid_rows, 'lower'] <= result.loc[valid_rows, 'middle']).all()
        assert (result.loc[valid_rows, 'middle'] <= result.loc[valid_rows, 'upper']).all()


@given(
    prices=st.lists(
        st.integers(min_value=10000, max_value=100000),
        min_size=25,
        max_size=100
    ),
    period=st.integers(min_value=5, max_value=20)
)
@settings(deadline=None)
def test_bollinger_bands_bandwidth_always_nonnegative(prices, period):
    """Property: bandwidth must ALWAYS be >= 0."""
    from src.indicators.bollinger import calculate_bollinger_bands

    dates = pd.date_range('2024-01-01', periods=len(prices), freq='D')
    close_prices = pd.Series(prices, index=dates, dtype=float)

    result = calculate_bollinger_bands(
        close_prices=close_prices,
        period=period,
        std_multiplier=2.0
    )

    # Filter out NaN rows
    valid_rows = result['bandwidth'].notna()

    if valid_rows.sum() > 0:
        # Invariant: bandwidth >= 0
        assert (result.loc[valid_rows, 'bandwidth'] >= 0).all()


@given(
    constant_price=st.integers(min_value=10000, max_value=100000),
    length=st.integers(min_value=25, max_value=100),
    period=st.integers(min_value=5, max_value=20)
)
@settings(deadline=None)
def test_bollinger_bands_constant_prices_zero_bandwidth(constant_price, length, period):
    """Property: constant prices => bandwidth = 0 (no volatility)."""
    from src.indicators.bollinger import calculate_bollinger_bands

    # All prices identical
    dates = pd.date_range('2024-01-01', periods=length, freq='D')
    close_prices = pd.Series([float(constant_price)] * length, index=dates)

    result = calculate_bollinger_bands(
        close_prices=close_prices,
        period=period,
        std_multiplier=2.0
    )

    # Filter out NaN rows
    valid_rows = result['bandwidth'].notna()

    if valid_rows.sum() > 0:
        # Invariant: constant prices => std = 0 => bandwidth = 0
        assert np.allclose(result.loc[valid_rows, 'bandwidth'], 0, atol=1e-9)

        # Also verify upper = middle = lower
        assert np.allclose(
            result.loc[valid_rows, 'upper'],
            result.loc[valid_rows, 'middle'],
            atol=1e-6
        )
        assert np.allclose(
            result.loc[valid_rows, 'lower'],
            result.loc[valid_rows, 'middle'],
            atol=1e-6
        )


@given(
    prices=st.lists(
        st.integers(min_value=10000, max_value=100000),
        min_size=25,
        max_size=100
    ),
    period=st.integers(min_value=5, max_value=20),
    multiplier1=st.floats(min_value=1.0, max_value=2.0),
    multiplier2=st.floats(min_value=2.5, max_value=3.5)
)
@settings(deadline=None)
def test_bollinger_bands_larger_multiplier_wider_bands(prices, period, multiplier1, multiplier2):
    """Property: larger std_multiplier => wider bandwidth."""
    from src.indicators.bollinger import calculate_bollinger_bands

    assume(multiplier2 > multiplier1)

    dates = pd.date_range('2024-01-01', periods=len(prices), freq='D')
    close_prices = pd.Series(prices, index=dates, dtype=float)

    result1 = calculate_bollinger_bands(
        close_prices=close_prices,
        period=period,
        std_multiplier=multiplier1
    )

    result2 = calculate_bollinger_bands(
        close_prices=close_prices,
        period=period,
        std_multiplier=multiplier2
    )

    # Filter out NaN rows
    valid_rows = result1['bandwidth'].notna() & result2['bandwidth'].notna()

    if valid_rows.sum() > 0:
        # Invariant: larger multiplier => wider bandwidth
        # Allow small tolerance for floating point precision
        assert (result2.loc[valid_rows, 'bandwidth'] >= result1.loc[valid_rows, 'bandwidth'] - 1e-9).all()


@given(
    prices=st.lists(
        st.integers(min_value=10000, max_value=100000),
        min_size=25,
        max_size=100
    ),
    period=st.integers(min_value=5, max_value=20),
    std_multiplier=st.floats(min_value=1.5, max_value=2.5)
)
@settings(deadline=None)
def test_bollinger_bands_middle_within_price_range(prices, period, std_multiplier):
    """Property: middle band should be within min/max of recent prices."""
    from src.indicators.bollinger import calculate_bollinger_bands

    dates = pd.date_range('2024-01-01', periods=len(prices), freq='D')
    close_prices = pd.Series(prices, index=dates, dtype=float)

    result = calculate_bollinger_bands(
        close_prices=close_prices,
        period=period,
        std_multiplier=std_multiplier
    )

    # Filter out NaN rows
    valid_rows = result['middle'].notna()

    if valid_rows.sum() > 0:
        # For each valid row, middle should be within [min, max] of recent 'period' prices
        for idx in result[valid_rows].index:
            idx_pos = close_prices.index.get_loc(idx)
            if idx_pos >= period - 1:
                recent_prices = close_prices.iloc[idx_pos - period + 1:idx_pos + 1]
                middle_value = result.loc[idx, 'middle']

                # Middle (SMA) must be within range of input prices
                assert recent_prices.min() <= middle_value <= recent_prices.max()


@given(
    prices=st.lists(
        st.integers(min_value=10000, max_value=100000),
        min_size=25,
        max_size=100
    ),
    period=st.integers(min_value=5, max_value=20),
    std_multiplier=st.floats(min_value=1.0, max_value=3.0)
)
@settings(deadline=None)
def test_bollinger_bands_result_length_matches_input(prices, period, std_multiplier):
    """Property: output DataFrame length must equal input Series length."""
    from src.indicators.bollinger import calculate_bollinger_bands

    dates = pd.date_range('2024-01-01', periods=len(prices), freq='D')
    close_prices = pd.Series(prices, index=dates, dtype=float)

    result = calculate_bollinger_bands(
        close_prices=close_prices,
        period=period,
        std_multiplier=std_multiplier
    )

    # Invariant: output length = input length
    assert len(result) == len(close_prices)


@given(
    prices=st.lists(
        st.integers(min_value=10000, max_value=100000),
        min_size=25,
        max_size=100
    ),
    period=st.integers(min_value=5, max_value=20),
    std_multiplier=st.floats(min_value=1.0, max_value=3.0)
)
@settings(deadline=None)
def test_bollinger_bands_nan_pattern(prices, period, std_multiplier):
    """Property: First (period-1) rows should be NaN, rest should be valid."""
    from src.indicators.bollinger import calculate_bollinger_bands

    dates = pd.date_range('2024-01-01', periods=len(prices), freq='D')
    close_prices = pd.Series(prices, index=dates, dtype=float)

    result = calculate_bollinger_bands(
        close_prices=close_prices,
        period=period,
        std_multiplier=std_multiplier
    )

    # First (period-1) rows should be NaN
    assert result['middle'].iloc[:period-1].isna().all()

    # From period onwards, should have valid values (not NaN)
    if len(prices) >= period:
        assert result['middle'].iloc[period-1:].notna().all()
        assert result['upper'].iloc[period-1:].notna().all()
        assert result['lower'].iloc[period-1:].notna().all()
        assert result['bandwidth'].iloc[period-1:].notna().all()
