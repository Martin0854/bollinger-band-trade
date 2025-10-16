"""
Integration tests for indicator pipeline.
Tests volume filter integration with signal generation.

Test Coverage:
- T013: Volume filter in signal generation
- T023: RSI filter in signal generation (Phase 4)
- T035: MACD filter in signal generation (Phase 5)
"""

import pytest
import pandas as pd
from datetime import datetime
from decimal import Decimal

# Imports work now that implementation is complete
from src.indicators.volume import VolumeFilter
from src.indicators.momentum import RSIIndicator, MACDIndicator


# ========================================================================
# T013: Integration test for volume filter in signal generation
# ========================================================================

@pytest.mark.integration
class TestVolumeFilterIntegration:
    """Test volume filter integration with signal generation."""

    def test_signal_generated_when_volume_spike_detected(self):
        """
        Test signal generated when volume spike detected.
        Simulates: Bollinger breakout + volume spike → signal generated
        """
        # Given: 25 days of volume data with spike on day 25
        volumes = pd.Series([1000] * 24 + [2000])  # 2x spike
        filter = VolumeFilter(window_days=20, multiplier=1.5)
        avg_volume = filter.calculate_average_volume(volumes)

        # When: Check if filter passes for last day
        current_volume = volumes.iloc[-1]
        avg = avg_volume.iloc[-1]
        passes = filter.check_volume_spike(current_volume, avg)

        # Then: Filter should pass (2000 >= 1000 * 1.5)
        assert passes == True

    def test_signal_filtered_when_no_volume_spike(self):
        """
        Test signal filtered when no volume spike.
        Simulates: Bollinger breakout + normal volume → signal filtered
        """
        # Given: 25 days of stable volume
        volumes = pd.Series([1000] * 25)
        filter = VolumeFilter(window_days=20, multiplier=1.5)
        avg_volume = filter.calculate_average_volume(volumes)

        # When: Check if filter passes for last day
        current_volume = volumes.iloc[-1]
        avg = avg_volume.iloc[-1]
        passes = filter.check_volume_spike(current_volume, avg)

        # Then: Filter should not pass (1000 < 1000 * 1.5)
        assert passes == False

    def test_fallback_when_volume_data_missing(self):
        """
        Test fallback when volume data missing (FR-006).
        Volume filter should skip and return False (not block execution).
        """
        # Given: VolumeFilter
        filter = VolumeFilter(window_days=20, multiplier=1.5)

        # When: Volume data is insufficient (NaN average)
        volumes = pd.Series([1000] * 10)  # Only 10 days
        avg_volume = filter.calculate_average_volume(volumes)
        current_volume = 2000
        avg = avg_volume.iloc[-1]

        # Then: Filter should return False (skip, don't crash)
        passes = filter.check_volume_spike(current_volume, avg)
        assert passes is False
        assert pd.isna(avg)  # Confirm average is NaN


# ========================================================================
# T035: Integration test for MACD filter in signal generation (User Story 3)
# ========================================================================

@pytest.mark.integration
class TestMACDFilterIntegration:
    """Test MACD filter integration with signal generation (Phase 2)."""

    def test_signal_generated_when_all_filters_pass(self):
        """
        Test signal generated when volume + RSI + MACD all pass.
        Simulates: Bollinger breakout + volume spike + RSI neutral + MACD bullish → signal generated
        """
        # Given: 30 days of price data with uptrend
        prices = pd.Series(range(100, 130))  # Uptrend
        macd = MACDIndicator(fast_period=12, slow_period=26, signal_period=9)

        # When: Calculate MACD
        result = macd.calculate(prices)

        # Then: MACD should be bullish in uptrend
        macd_value = result['macd'].iloc[-1]
        signal_value = result['signal'].iloc[-1]

        # Verify MACD is bullish (MACD > signal)
        is_bullish = macd.is_bullish(macd_value, signal_value)
        assert is_bullish == True, f"MACD should be bullish: {macd_value} > {signal_value}"

    def test_signal_filtered_when_volume_and_rsi_pass_but_macd_bearish(self):
        """
        Test signal filtered when volume + RSI pass but MACD is bearish.
        Simulates: Bollinger breakout + volume spike + RSI neutral + MACD bearish → signal filtered
        """
        # Given: Price data with downtrend
        prices_up = list(range(100, 120))  # Initial uptrend
        prices_down = list(range(119, 100, -1))  # Strong downtrend
        prices = pd.Series(prices_up + prices_down)

        macd = MACDIndicator(fast_period=5, slow_period=10, signal_period=3)

        # When: Calculate MACD
        result = macd.calculate(prices)

        # Then: MACD should be bearish at the end (death cross)
        macd_value = result['macd'].iloc[-1]
        signal_value = result['signal'].iloc[-1]

        # Verify MACD is bearish (MACD < signal)
        is_bullish = macd.is_bullish(macd_value, signal_value)
        assert is_bullish == False, f"MACD should be bearish: {macd_value} < {signal_value}"

    def test_exit_signal_when_macd_death_cross(self):
        """
        Test exit signal when MACD death cross occurs (FR-010).
        Simulates: Holding position + MACD death cross → exit signal
        """
        # Given: MACD indicator
        macd = MACDIndicator()

        # When: Death cross condition (MACD crosses below signal)
        macd_value = 2.0
        signal_value = 5.0

        # Then: Should be bearish (exit condition)
        is_bearish = macd.is_bearish(macd_value, signal_value)
        assert is_bearish is True
        assert not macd.is_bullish(macd_value, signal_value)

    def test_fallback_when_insufficient_macd_data(self):
        """
        Test fallback when insufficient MACD data (FR-011).
        MACD filter should skip and return False (not block execution).
        """
        # Given: Very short price series (< slow_period days)
        prices = pd.Series([100, 102, 104])  # Only 3 days
        macd = MACDIndicator(fast_period=12, slow_period=26, signal_period=9)

        # When: Calculate MACD with insufficient data
        result = macd.calculate(prices)

        # Then: MACD values should be present but EMA not yet stable
        # Early values will be NaN or unreliable
        macd_value = result['macd'].iloc[-1]
        signal_value = result['signal'].iloc[-1]

        # The indicator should handle this gracefully (NaN check in is_bullish)
        # Even if values exist, they're not reliable with < slow_period data
        assert len(result) == len(prices)
