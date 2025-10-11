"""
Unit tests for Squeeze detection (data-model.md Entity 5).
Tests 30% band width decrease over 10 days, direction_bias logic, expansion confirmation.

These tests MUST FAIL initially (TDD) until src/indicators/squeeze.py is implemented.
"""

import pytest
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime, timedelta


def test_squeeze_detection_basic():
    """Test squeeze is detected when band width decreases by 30% over 10 days."""
    from src.indicators.squeeze import detect_squeeze

    # Create band width data: 5000 -> 3500 (30% decrease)
    dates = pd.date_range('2024-01-01', periods=20, freq='D')
    band_width = pd.Series([5000] * 10 + [3500] * 10, index=dates)

    result = detect_squeeze(
        band_width=band_width,
        lookback_days=10,
        threshold_percent=30.0
    )

    # Should detect squeeze on day 10 (index 9)
    assert result.iloc[10] == True  # Day 11: comparing to day 1


def test_squeeze_detection_no_squeeze():
    """Test no squeeze detected when band width decrease is < 30%."""
    from src.indicators.squeeze import detect_squeeze

    # Create band width data: 5000 -> 4000 (20% decrease - below threshold)
    dates = pd.date_range('2024-01-01', periods=20, freq='D')
    band_width = pd.Series([5000] * 10 + [4000] * 10, index=dates)

    result = detect_squeeze(
        band_width=band_width,
        lookback_days=10,
        threshold_percent=30.0
    )

    # Should NOT detect squeeze (decrease only 20%)
    assert result.iloc[10] == False


def test_squeeze_detection_exact_threshold():
    """Test squeeze detection at exact 30% threshold."""
    from src.indicators.squeeze import detect_squeeze

    # Create band width data: 5000 -> 3500 (exactly 30% decrease)
    dates = pd.date_range('2024-01-01', periods=20, freq='D')
    band_width = pd.Series([5000] * 10 + [3500] * 10, index=dates)

    result = detect_squeeze(
        band_width=band_width,
        lookback_days=10,
        threshold_percent=30.0
    )

    # Should detect squeeze at exactly 30%
    assert result.iloc[10] == True


def test_squeeze_detection_insufficient_data():
    """Test squeeze detection handles insufficient historical data."""
    from src.indicators.squeeze import detect_squeeze

    # Only 5 days of data, but lookback is 10 days
    dates = pd.date_range('2024-01-01', periods=5, freq='D')
    band_width = pd.Series([5000, 4500, 4000, 3500, 3000], index=dates)

    result = detect_squeeze(
        band_width=band_width,
        lookback_days=10,
        threshold_percent=30.0
    )

    # First 10 days should be False (insufficient data)
    assert result.iloc[:5].all() == False


def test_squeeze_direction_bias_upper():
    """Test direction_bias = 'upper' when price touches upper band during squeeze."""
    from src.indicators.squeeze import determine_direction_bias

    # Price touches upper band
    dates = pd.date_range('2024-01-01', periods=10, freq='D')
    close_prices = pd.Series([65000] * 10, index=dates)
    upper_band = pd.Series([65000] * 10, index=dates)
    lower_band = pd.Series([55000] * 10, index=dates)

    direction = determine_direction_bias(
        close_prices=close_prices,
        upper_band=upper_band,
        lower_band=lower_band,
        squeeze_start_idx=0,
        squeeze_end_idx=9
    )

    assert direction == "upper"


def test_squeeze_direction_bias_lower():
    """Test direction_bias = 'lower' when price touches lower band during squeeze."""
    from src.indicators.squeeze import determine_direction_bias

    # Price touches lower band
    dates = pd.date_range('2024-01-01', periods=10, freq='D')
    close_prices = pd.Series([55000] * 10, index=dates)
    upper_band = pd.Series([65000] * 10, index=dates)
    lower_band = pd.Series([55000] * 10, index=dates)

    direction = determine_direction_bias(
        close_prices=close_prices,
        upper_band=upper_band,
        lower_band=lower_band,
        squeeze_start_idx=0,
        squeeze_end_idx=9
    )

    assert direction == "lower"


def test_squeeze_direction_bias_neutral():
    """Test direction_bias = None when price doesn't touch either band."""
    from src.indicators.squeeze import determine_direction_bias

    # Price stays in middle, doesn't touch bands
    dates = pd.date_range('2024-01-01', periods=10, freq='D')
    close_prices = pd.Series([60000] * 10, index=dates)
    upper_band = pd.Series([65000] * 10, index=dates)
    lower_band = pd.Series([55000] * 10, index=dates)

    direction = determine_direction_bias(
        close_prices=close_prices,
        upper_band=upper_band,
        lower_band=lower_band,
        squeeze_start_idx=0,
        squeeze_end_idx=9
    )

    assert direction is None


def test_squeeze_expansion_confirmation():
    """Test expansion is confirmed when band width increases after squeeze."""
    from src.indicators.squeeze import confirm_expansion

    # Band width: squeeze (3000) then expand (4500 = 50% increase)
    dates = pd.date_range('2024-01-01', periods=20, freq='D')
    band_width = pd.Series([3000] * 10 + [4500] * 10, index=dates)

    is_expansion = confirm_expansion(
        band_width=band_width,
        squeeze_end_date=dates[9],
        expansion_threshold_percent=20.0
    )

    assert is_expansion == True


def test_squeeze_no_expansion():
    """Test expansion not confirmed when band width increase is insufficient."""
    from src.indicators.squeeze import confirm_expansion

    # Band width: squeeze (3000) then slight increase (3300 = 10% increase)
    dates = pd.date_range('2024-01-01', periods=20, freq='D')
    band_width = pd.Series([3000] * 10 + [3300] * 10, index=dates)

    is_expansion = confirm_expansion(
        band_width=band_width,
        squeeze_end_date=dates[9],
        expansion_threshold_percent=20.0
    )

    assert is_expansion == False


def test_squeeze_create_squeeze_event():
    """Test SqueezeEvent creation with all required fields."""
    from src.indicators.squeeze import SqueezeEvent

    event = SqueezeEvent(
        stock_code="005930",
        detection_date=datetime(2024, 1, 15),
        band_width_at_detection=Decimal('3000'),
        band_width_N_days_ago=Decimal('5000'),
        lookback_days=10,
        threshold_percent=Decimal('30'),
        direction_bias="upper"
    )

    assert event.stock_code == "005930"
    assert event.direction_bias == "upper"
    assert event.width_decrease_pct == Decimal('40')  # (5000-3000)/5000 = 40%


def test_squeeze_event_width_decrease_calculation():
    """Test SqueezeEvent calculates width_decrease_pct correctly."""
    from src.indicators.squeeze import SqueezeEvent

    event = SqueezeEvent(
        stock_code="005930",
        detection_date=datetime(2024, 1, 15),
        band_width_at_detection=Decimal('3500'),
        band_width_N_days_ago=Decimal('5000'),
        lookback_days=10,
        threshold_percent=Decimal('30'),
        direction_bias="upper"
    )

    # (5000 - 3500) / 5000 * 100 = 30%
    assert event.width_decrease_pct == Decimal('30')


def test_squeeze_event_to_log_dict():
    """Test SqueezeEvent.to_log_dict() for database logging."""
    from src.indicators.squeeze import SqueezeEvent

    event = SqueezeEvent(
        stock_code="005930",
        detection_date=datetime(2024, 1, 15, 9, 0, 0),
        band_width_at_detection=Decimal('3000'),
        band_width_N_days_ago=Decimal('5000'),
        lookback_days=10,
        threshold_percent=Decimal('30'),
        direction_bias="upper"
    )

    log_dict = event.to_log_dict()

    assert 'event_id' in log_dict
    assert log_dict['stock_code'] == "005930"
    assert log_dict['detection_date'] == "2024-01-15T09:00:00"
    assert log_dict['band_width_at_detection'] == 3000.0
    assert log_dict['width_decrease_pct'] == 40.0
    assert log_dict['direction_bias'] == "upper"


def test_squeeze_validation_lookback_positive():
    """Test squeeze detection validates lookback_days > 0."""
    from src.indicators.squeeze import detect_squeeze

    dates = pd.date_range('2024-01-01', periods=20, freq='D')
    band_width = pd.Series([5000] * 20, index=dates)

    with pytest.raises(ValueError, match="lookback_days"):
        detect_squeeze(
            band_width=band_width,
            lookback_days=0,  # Invalid
            threshold_percent=30.0
        )


def test_squeeze_validation_threshold_range():
    """Test squeeze detection validates threshold_percent in [0, 100]."""
    from src.indicators.squeeze import detect_squeeze

    dates = pd.date_range('2024-01-01', periods=20, freq='D')
    band_width = pd.Series([5000] * 20, index=dates)

    with pytest.raises(ValueError, match="threshold_percent"):
        detect_squeeze(
            band_width=band_width,
            lookback_days=10,
            threshold_percent=150.0  # Invalid: > 100
        )


def test_squeeze_multiple_squeezes():
    """Test detecting multiple squeeze events in a series."""
    from src.indicators.squeeze import detect_squeeze

    # Two squeeze periods: days 10-15 and days 25-30
    dates = pd.date_range('2024-01-01', periods=40, freq='D')
    band_width_values = (
        [5000] * 10 +  # Normal
        [3000] * 5 +   # Squeeze 1
        [5000] * 10 +  # Normal
        [3000] * 5 +   # Squeeze 2
        [5000] * 10    # Normal
    )
    band_width = pd.Series(band_width_values, index=dates)

    result = detect_squeeze(
        band_width=band_width,
        lookback_days=10,
        threshold_percent=30.0
    )

    # Should detect both squeezes
    assert result.iloc[10:15].any()  # First squeeze
    assert result.iloc[25:30].any()  # Second squeeze
