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
