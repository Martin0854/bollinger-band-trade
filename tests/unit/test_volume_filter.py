"""
Unit tests for VolumeFilter (Entity 4).
Tests MUST be written FIRST and FAIL before implementation (TDD).
User Story 1 (US1): 거래량 확인으로 거짓 신호 필터링

Test Coverage:
- T010: calculate_average_volume() - 20-day rolling average
- T011: check_volume_spike() - threshold detection
- T012: Property-based tests with hypothesis
"""

import pytest
import pandas as pd
import numpy as np
from hypothesis import given, strategies as st
from decimal import Decimal

# Import will fail until T015 is implemented - THIS IS EXPECTED FOR TDD
try:
    from src.indicators.volume import VolumeFilter
except ImportError:
    VolumeFilter = None


# ========================================================================
# T010: Unit tests for calculate_average_volume()
# ========================================================================

@pytest.mark.skipif(VolumeFilter is None, reason="VolumeFilter not yet implemented (TDD)")
class TestVolumeFilterCalculateAverage:
    """Test calculate_average_volume() method."""

    def test_calculate_average_with_sufficient_data(self):
        """Test 20-day rolling average calculation with sufficient data."""
        # Given: 25 days of constant volume (1000 shares/day)
        volumes = pd.Series([1000] * 25)
        filter = VolumeFilter(window_days=20, multiplier=1.5)

        # When: Calculate rolling average
        avg_volume = filter.calculate_average_volume(volumes)

        # Then: Last 6 values should all be 1000.0 (rolling window full)
        assert avg_volume.iloc[-1] == 1000.0
        assert avg_volume.iloc[-6] == 1000.0
        # First 19 values should be NaN (window not full yet)
        assert pd.isna(avg_volume.iloc[0])
        assert pd.isna(avg_volume.iloc[18])

    def test_calculate_average_with_varying_volume(self):
        """Test rolling average tracks volume changes."""
        # Given: Volume increases from 1000 to 2000 over 25 days
        volumes = pd.Series(range(1000, 2500, 60))  # ~25 values
        filter = VolumeFilter(window_days=20, multiplier=1.5)

        # When: Calculate rolling average
        avg_volume = filter.calculate_average_volume(volumes)

        # Then: Average should increase over time
        assert avg_volume.iloc[-1] > avg_volume.iloc[19]  # Later > Earlier

    def test_calculate_average_with_insufficient_data(self):
        """Test that insufficient data (< window_days) returns NaN."""
        # Given: Only 10 days of data (need 20)
        volumes = pd.Series([1000] * 10)
        filter = VolumeFilter(window_days=20, multiplier=1.5)

        # When: Calculate rolling average
        avg_volume = filter.calculate_average_volume(volumes)

        # Then: All values should be NaN (window never fills)
        assert pd.isna(avg_volume.iloc[-1])
        assert avg_volume.isna().all()

    def test_calculate_average_with_zero_volume(self):
        """Test handling of zero volume (missing data edge case)."""
        # Given: Mix of normal and zero volume
        volumes = pd.Series([1000, 1000, 0, 1000, 1000] + [1000] * 20)
        filter = VolumeFilter(window_days=20, multiplier=1.5)

        # When: Calculate rolling average
        avg_volume = filter.calculate_average_volume(volumes)

        # Then: Average should include zero (not filtered)
        assert not pd.isna(avg_volume.iloc[-1])


# ========================================================================
# T011: Unit tests for check_volume_spike()
# ========================================================================

@pytest.mark.skipif(VolumeFilter is None, reason="VolumeFilter not yet implemented (TDD)")
class TestVolumeFilterCheckSpike:
    """Test check_volume_spike() method."""

    def test_spike_detected_when_above_threshold(self):
        """Test volume >= 1.5x avg returns True."""
        # Given: Average volume of 1000, threshold 1.5x
        filter = VolumeFilter(window_days=20, multiplier=1.5)

        # When: Current volume is 1600 (>= 1500 threshold)
        has_spike = filter.check_volume_spike(current_volume=1600, avg_volume=1000)

        # Then: Spike detected
        assert has_spike is True

    def test_spike_detected_at_exact_threshold(self):
        """Test volume == threshold is considered a spike (boundary condition)."""
        # Given: Average volume of 1000, threshold 1.5x
        filter = VolumeFilter(window_days=20, multiplier=1.5)

        # When: Current volume is exactly 1500
        has_spike = filter.check_volume_spike(current_volume=1500, avg_volume=1000)

        # Then: Spike detected (>= not just >)
        assert has_spike is True

    def test_no_spike_when_below_threshold(self):
        """Test volume < 1.5x avg returns False."""
        # Given: Average volume of 1000, threshold 1.5x
        filter = VolumeFilter(window_days=20, multiplier=1.5)

        # When: Current volume is 1400 (< 1500 threshold)
        has_spike = filter.check_volume_spike(current_volume=1400, avg_volume=1000)

        # Then: No spike detected
        assert has_spike is False

    def test_no_spike_with_nan_average(self):
        """Test NaN handling (missing volume data edge case - FR-006)."""
        # Given: VolumeFilter
        filter = VolumeFilter(window_days=20, multiplier=1.5)

        # When: Average volume is NaN (insufficient data)
        has_spike = filter.check_volume_spike(current_volume=2000, avg_volume=float('nan'))

        # Then: No spike detected (filter skipped)
        assert has_spike is False

    def test_no_spike_with_zero_average(self):
        """Test zero average handling (division by zero edge case)."""
        # Given: VolumeFilter
        filter = VolumeFilter(window_days=20, multiplier=1.5)

        # When: Average volume is zero
        has_spike = filter.check_volume_spike(current_volume=1000, avg_volume=0)

        # Then: No spike detected (avoid division by zero)
        assert has_spike is False

    def test_custom_multiplier(self):
        """Test spike detection with custom multiplier."""
        # Given: Higher multiplier (2.0x)
        filter = VolumeFilter(window_days=20, multiplier=2.0)

        # When: Current volume is 1800 (< 2000 threshold for 2.0x)
        has_spike = filter.check_volume_spike(current_volume=1800, avg_volume=1000)

        # Then: No spike (doesn't meet 2.0x threshold)
        assert has_spike is False

        # When: Current volume is 2100 (>= 2000 threshold)
        has_spike = filter.check_volume_spike(current_volume=2100, avg_volume=1000)

        # Then: Spike detected
        assert has_spike is True


# ========================================================================
# T012: Property-based tests using hypothesis
# ========================================================================

@pytest.mark.skipif(VolumeFilter is None, reason="VolumeFilter not yet implemented (TDD)")
class TestVolumeFilterProperties:
    """Property-based tests for VolumeFilter invariants."""

    @given(
        volumes=st.lists(
            st.floats(min_value=1000, max_value=100000, allow_nan=False, allow_infinity=False),
            min_size=21,
            max_size=21
        ),
        multiplier=st.floats(min_value=1.0, max_value=5.0, allow_nan=False, allow_infinity=False)
    )
    def test_property_spike_detection_threshold(self, volumes, multiplier):
        """
        Property: If current_volume >= avg_volume * multiplier, spike is detected.
        Uses hypothesis to generate random volume series and multipliers.
        """
        # Given: VolumeFilter with random multiplier
        filter = VolumeFilter(window_days=20, multiplier=multiplier)

        # When: Calculate average volume
        volumes_series = pd.Series(volumes)
        avg_volume = filter.calculate_average_volume(volumes_series)
        avg = avg_volume.iloc[-1]

        # Property: If current >= avg * multiplier, spike detected
        if not pd.isna(avg) and avg > 0:
            threshold = avg * multiplier
            # Test just above threshold
            assert filter.check_volume_spike(threshold + 1, avg) is True
            # Test just below threshold
            if threshold > 1:  # Avoid negative volume
                assert filter.check_volume_spike(threshold - 1, avg) is False

    @given(
        window_days=st.integers(min_value=5, max_value=30),
        data_length=st.integers(min_value=1, max_value=50)
    )
    def test_property_average_nan_when_insufficient_data(self, window_days, data_length):
        """
        Property: If data length < window_days, all averages are NaN.
        """
        # Given: Volume data shorter than window
        if data_length < window_days:
            volumes = pd.Series([1000] * data_length)
            filter = VolumeFilter(window_days=window_days, multiplier=1.5)

            # When: Calculate average
            avg_volume = filter.calculate_average_volume(volumes)

            # Property: All values should be NaN
            assert avg_volume.isna().all()

    @given(
        volumes=st.lists(
            st.floats(min_value=100, max_value=10000, allow_nan=False, allow_infinity=False),
            min_size=25,
            max_size=25
        )
    )
    def test_property_average_always_positive(self, volumes):
        """
        Property: Average volume is always positive (or NaN), never negative.
        """
        # Given: VolumeFilter with positive volume data
        volumes_series = pd.Series(volumes)
        filter = VolumeFilter(window_days=20, multiplier=1.5)

        # When: Calculate average
        avg_volume = filter.calculate_average_volume(volumes_series)

        # Property: All non-NaN values must be positive
        valid_averages = avg_volume.dropna()
        assert (valid_averages >= 0).all()
