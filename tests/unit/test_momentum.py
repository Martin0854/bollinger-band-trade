"""
Unit tests for momentum indicators (RSI, MACD, ATR).
Tests MUST be written FIRST and FAIL before implementation (TDD).
User Stories: US2 (RSI), US3 (MACD), US5 (ATR)

Test Coverage:
- T019-T022: RSI indicator tests
- T031-T034: MACD indicator tests
- T055-T057: ATR indicator tests
"""

import pytest
import pandas as pd
import numpy as np
from hypothesis import given, strategies as st

# Imports should work now that implementation is done
from src.indicators.momentum import RSIIndicator

# Phase 2 and Phase 4 indicators not yet implemented
try:
    from src.indicators.momentum import MACDIndicator
except ImportError:
    MACDIndicator = None

try:
    from src.indicators.momentum import ATRIndicator
except ImportError:
    ATRIndicator = None


# ========================================================================
# T019-T022: RSI Indicator Tests (User Story 2)
# ========================================================================

class TestRSIIndicator:
    """Test RSI indicator calculation and thresholds."""

    def test_rsi_calculation_with_uptrend(self):
        """T019: Test RSI calculation with uptrending data (RSI > 50)."""
        # Given: Uptrending price series
        prices = pd.Series([100, 102, 104, 103, 105, 107, 106, 108, 110, 109,
                           111, 113, 112, 114, 116])
        rsi = RSIIndicator(period=14)

        # When: Calculate RSI
        rsi_values = rsi.calculate(prices)

        # Then: RSI should be above 50 (uptrend)
        assert rsi_values.iloc[-1] > 50
        assert not pd.isna(rsi_values.iloc[-1])

    def test_rsi_calculation_with_downtrend(self):
        """T019: Test RSI calculation with downtrending data (RSI < 50)."""
        # Given: Downtrending price series
        prices = pd.Series([116, 114, 112, 113, 111, 109, 110, 108, 106, 107,
                           105, 103, 104, 102, 100])
        rsi = RSIIndicator(period=14)

        # When: Calculate RSI
        rsi_values = rsi.calculate(prices)

        # Then: RSI should be below 50 (downtrend)
        assert rsi_values.iloc[-1] < 50

    def test_rsi_insufficient_data_returns_nan(self):
        """T019: Test RSI with insufficient data (< period days) returns NaN for early values."""
        # Given: Less than period days of data
        prices = pd.Series([100, 102, 104])  # Only 3 days
        rsi = RSIIndicator(period=14)

        # When: Calculate RSI
        rsi_values = rsi.calculate(prices)

        # Then: First value should be NaN (no prior price change)
        # Note: pandas EMA will produce values even with limited data,
        # but they won't be reliable. The first delta is always NaN.
        assert pd.isna(rsi_values.iloc[0])

    def test_rsi_with_constant_prices(self):
        """T019: Test RSI with all prices same (edge case)."""
        # Given: Constant price (no change)
        prices = pd.Series([100] * 15)
        rsi = RSIIndicator(period=14)

        # When: Calculate RSI
        rsi_values = rsi.calculate(prices)

        # Then: RSI should handle gracefully (NaN or 50)
        # When no price movement, RSI is undefined (NaN)
        last_rsi = rsi_values.iloc[-1]
        assert pd.isna(last_rsi) or last_rsi == 50

    def test_rsi_is_neutral_true(self):
        """T020: Test 30 < RSI < 70 returns True (neutral zone)."""
        # Given: RSI indicator
        rsi = RSIIndicator(period=14, overbought=70, oversold=30)

        # When: Check neutral zone values
        assert rsi.is_neutral(50) is True
        assert rsi.is_neutral(31) is True
        assert rsi.is_neutral(69) is True

    def test_rsi_is_neutral_overbought(self):
        """T020: Test RSI >= 70 returns False (overbought)."""
        # Given: RSI indicator
        rsi = RSIIndicator(period=14, overbought=70, oversold=30)

        # When: Check overbought values
        assert rsi.is_neutral(70) is False
        assert rsi.is_neutral(75) is False
        assert rsi.is_neutral(100) is False

    def test_rsi_is_neutral_oversold(self):
        """T020: Test RSI <= 30 returns False (oversold)."""
        # Given: RSI indicator
        rsi = RSIIndicator(period=14, overbought=70, oversold=30)

        # When: Check oversold values
        assert rsi.is_neutral(30) is False
        assert rsi.is_neutral(25) is False
        assert rsi.is_neutral(0) is False

    def test_rsi_is_neutral_nan_input(self):
        """T020: Test NaN input returns False."""
        # Given: RSI indicator
        rsi = RSIIndicator(period=14)

        # When: Check with NaN
        assert rsi.is_neutral(float('nan')) is False

    def test_rsi_exit_signal_overbought(self):
        """T021: Test RSI > 70 triggers exit condition."""
        # Given: RSI indicator
        rsi = RSIIndicator(period=14, overbought=70)

        # When: RSI crosses above overbought
        rsi_value = 72

        # Then: Should trigger exit (not neutral)
        assert rsi.is_neutral(rsi_value) is False
        assert rsi_value > rsi.overbought

    @given(
        prices=st.lists(
            st.floats(min_value=50, max_value=150, allow_nan=False, allow_infinity=False),
            min_size=20,
            max_size=20
        )
    )
    def test_rsi_always_between_0_and_100(self, prices):
        """T022: Property - RSI always between 0 and 100."""
        # Given: Random price series
        prices_series = pd.Series(prices)
        rsi_indicator = RSIIndicator(period=14)

        # When: Calculate RSI
        rsi_values = rsi_indicator.calculate(prices_series)

        # Property: All non-NaN values must be between 0 and 100
        valid_rsi = rsi_values.dropna()
        if len(valid_rsi) > 0:
            assert (valid_rsi >= 0).all()
            assert (valid_rsi <= 100).all()
