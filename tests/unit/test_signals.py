"""
Unit tests for Signal generation (data-model.md Entity 6).
Tests entry/exit signal logic based on squeeze expansion and band crossings.

These tests MUST FAIL initially (TDD) until src/signals/generator.py is implemented.
"""

import pytest
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime, timedelta
import pytz


def test_entry_signal_after_squeeze_upper():
    """Test BUY signal generated when price breaks above upper band after squeeze with upper bias."""
    from src.signals.generator import generate_entry_signals

    dates = pd.date_range('2024-01-01', periods=20, freq='D')

    # Price breaks above upper band after squeeze
    close_prices = pd.Series([60000] * 10 + [66000] * 10, index=dates)
    upper_band = pd.Series([65000] * 20, index=dates)
    lower_band = pd.Series([55000] * 20, index=dates)

    # Squeeze detected on day 10, direction_bias = upper
    squeeze_events = [
        {
            'detection_date': dates[9],
            'direction_bias': 'upper',
            'expansion_confirmed': True
        }
    ]

    signals = generate_entry_signals(
        close_prices=close_prices,
        upper_band=upper_band,
        lower_band=lower_band,
        squeeze_events=squeeze_events
    )

    # Should generate BUY signal on day 10 (price > upper)
    assert signals.loc[dates[10], 'signal'] == 'BUY'
    assert signals.loc[dates[10], 'reason'] == 'squeeze_expansion_buy'


def test_entry_signal_after_squeeze_lower():
    """Test SHORT signal (or no signal if shorts disabled) when price breaks below lower band after squeeze."""
    from src.signals.generator import generate_entry_signals

    dates = pd.date_range('2024-01-01', periods=20, freq='D')

    # Price breaks below lower band after squeeze
    close_prices = pd.Series([60000] * 10 + [54000] * 10, index=dates)
    upper_band = pd.Series([65000] * 20, index=dates)
    lower_band = pd.Series([55000] * 20, index=dates)

    # Squeeze detected on day 10, direction_bias = lower
    squeeze_events = [
        {
            'detection_date': dates[9],
            'direction_bias': 'lower',
            'expansion_confirmed': True
        }
    ]

    signals = generate_entry_signals(
        close_prices=close_prices,
        upper_band=upper_band,
        lower_band=lower_band,
        squeeze_events=squeeze_events,
        allow_shorts=False  # FR-032: No short positions
    )

    # Should NOT generate signal (shorts disabled)
    assert signals.loc[dates[10], 'signal'] == 'HOLD'


def test_no_entry_signal_without_expansion():
    """Test no entry signal if squeeze not confirmed to expand."""
    from src.signals.generator import generate_entry_signals

    dates = pd.date_range('2024-01-01', periods=20, freq='D')

    close_prices = pd.Series([60000] * 10 + [66000] * 10, index=dates)
    upper_band = pd.Series([65000] * 20, index=dates)
    lower_band = pd.Series([55000] * 20, index=dates)

    # Squeeze detected but NOT confirmed to expand
    squeeze_events = [
        {
            'detection_date': dates[9],
            'direction_bias': 'upper',
            'expansion_confirmed': False  # Not expanded yet
        }
    ]

    signals = generate_entry_signals(
        close_prices=close_prices,
        upper_band=upper_band,
        lower_band=lower_band,
        squeeze_events=squeeze_events
    )

    # Should NOT generate signal (no expansion confirmation)
    assert signals.loc[dates[10], 'signal'] == 'HOLD'


def test_exit_signal_upper_band_touch():
    """Test SELL signal when price touches upper band (profit target)."""
    from src.signals.generator import generate_exit_signals

    dates = pd.date_range('2024-01-01', periods=20, freq='D')

    # Price touches upper band on day 15
    close_prices = pd.Series([60000] * 15 + [65000] * 5, index=dates)
    upper_band = pd.Series([65000] * 20, index=dates)
    middle_band = pd.Series([60000] * 20, index=dates)

    # Position held since day 5
    position_entry_date = dates[5]

    signals = generate_exit_signals(
        close_prices=close_prices,
        upper_band=upper_band,
        middle_band=middle_band,
        position_entry_date=position_entry_date
    )

    # Should generate SELL signal on day 15 (touched upper)
    assert signals.loc[dates[15], 'signal'] == 'SELL'
    assert signals.loc[dates[15], 'reason'] == 'band_upper_exit'


def test_exit_signal_middle_band_cross():
    """Test SELL signal when price crosses below middle band (stop loss alternative)."""
    from src.signals.generator import generate_exit_signals

    dates = pd.date_range('2024-01-01', periods=20, freq='D')

    # Price crosses below middle band on day 15
    close_prices = pd.Series([62000] * 15 + [58000] * 5, index=dates)
    upper_band = pd.Series([65000] * 20, index=dates)
    middle_band = pd.Series([60000] * 20, index=dates)

    position_entry_date = dates[5]

    signals = generate_exit_signals(
        close_prices=close_prices,
        upper_band=upper_band,
        middle_band=middle_band,
        position_entry_date=position_entry_date
    )

    # Should generate SELL signal on day 15 (crossed below middle)
    assert signals.loc[dates[15], 'signal'] == 'SELL'
    assert signals.loc[dates[15], 'reason'] == 'band_middle_cross'


def test_no_exit_signal_before_entry():
    """Test no exit signal generated before position entry date."""
    from src.signals.generator import generate_exit_signals

    dates = pd.date_range('2024-01-01', periods=20, freq='D')

    close_prices = pd.Series([65000] * 20, index=dates)  # At upper band
    upper_band = pd.Series([65000] * 20, index=dates)
    middle_band = pd.Series([60000] * 20, index=dates)

    # Position entered on day 10
    position_entry_date = dates[10]

    signals = generate_exit_signals(
        close_prices=close_prices,
        upper_band=upper_band,
        middle_band=middle_band,
        position_entry_date=position_entry_date
    )

    # Should NOT generate signals before entry date
    assert (signals.loc[:dates[9], 'signal'] == 'HOLD').all()


def test_signal_immutability():
    """Test Signal dataclass is immutable."""
    from src.signals.generator import Signal

    signal = Signal(
        date=datetime(2024, 1, 15, 9, 0, 0, tzinfo=pytz.timezone('Asia/Seoul')),
        stock_code="005930",
        signal_type="BUY",
        reason="squeeze_expansion_buy",
        price=Decimal('65000'),
        bollinger_values={
            'upper': Decimal('66000'),
            'middle': Decimal('60000'),
            'lower': Decimal('54000')
        }
    )

    # Should not be able to modify
    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        signal.signal_type = "SELL"


def test_signal_to_log_dict():
    """Test Signal.to_log_dict() for logging."""
    from src.signals.generator import Signal

    signal = Signal(
        date=datetime(2024, 1, 15, 9, 0, 0, tzinfo=pytz.timezone('Asia/Seoul')),
        stock_code="005930",
        signal_type="BUY",
        reason="squeeze_expansion_buy",
        price=Decimal('65000'),
        bollinger_values={
            'upper': Decimal('66000'),
            'middle': Decimal('60000'),
            'lower': Decimal('54000')
        }
    )

    log_dict = signal.to_log_dict()

    assert log_dict['stock_code'] == "005930"
    assert log_dict['signal'] == "buy"
    assert log_dict['reason'] == "squeeze_expansion_buy"
    assert log_dict['price'] == 65000.0
    assert log_dict['bollinger_upper'] == 66000.0


def test_multiple_signals_same_day():
    """Test handling multiple stocks with signals on same day."""
    from src.signals.generator import generate_entry_signals

    dates = pd.date_range('2024-01-01', periods=20, freq='D')

    # Two stocks, both generate signals
    close_prices_1 = pd.Series([66000] * 20, index=dates)
    close_prices_2 = pd.Series([67000] * 20, index=dates)

    upper_band = pd.Series([65000] * 20, index=dates)
    lower_band = pd.Series([55000] * 20, index=dates)

    squeeze_events_1 = [{
        'detection_date': dates[9],
        'direction_bias': 'upper',
        'expansion_confirmed': True
    }]

    squeeze_events_2 = [{
        'detection_date': dates[9],
        'direction_bias': 'upper',
        'expansion_confirmed': True
    }]

    signals_1 = generate_entry_signals(close_prices_1, upper_band, lower_band, squeeze_events_1)
    signals_2 = generate_entry_signals(close_prices_2, upper_band, lower_band, squeeze_events_2)

    # Both should generate BUY signals
    assert signals_1.loc[dates[10], 'signal'] == 'BUY'
    assert signals_2.loc[dates[10], 'signal'] == 'BUY'


def test_signal_validation_stock_code():
    """Test Signal validates stock_code format."""
    from src.signals.generator import Signal

    with pytest.raises(ValueError, match="stock_code"):
        Signal(
            date=datetime(2024, 1, 15, 9, 0, 0, tzinfo=pytz.timezone('Asia/Seoul')),
            stock_code="INVALID",  # Not 6 digits
            signal_type="BUY",
            reason="squeeze_expansion_buy",
            price=Decimal('65000'),
            bollinger_values={'upper': Decimal('66000'), 'middle': Decimal('60000'), 'lower': Decimal('54000')}
        )


def test_signal_validation_price_positive():
    """Test Signal validates price > 0."""
    from src.signals.generator import Signal

    with pytest.raises(ValueError, match="positive"):
        Signal(
            date=datetime(2024, 1, 15, 9, 0, 0, tzinfo=pytz.timezone('Asia/Seoul')),
            stock_code="005930",
            signal_type="BUY",
            reason="squeeze_expansion_buy",
            price=Decimal('0'),  # Invalid
            bollinger_values={'upper': Decimal('66000'), 'middle': Decimal('60000'), 'lower': Decimal('54000')}
        )


def test_no_duplicate_signals():
    """Test no duplicate signals generated on same day for same stock."""
    from src.signals.generator import generate_entry_signals

    dates = pd.date_range('2024-01-01', periods=20, freq='D')

    close_prices = pd.Series([66000] * 20, index=dates)
    upper_band = pd.Series([65000] * 20, index=dates)
    lower_band = pd.Series([55000] * 20, index=dates)

    # Multiple squeeze events (shouldn't produce duplicate signals)
    squeeze_events = [
        {'detection_date': dates[9], 'direction_bias': 'upper', 'expansion_confirmed': True},
        {'detection_date': dates[9], 'direction_bias': 'upper', 'expansion_confirmed': True},
    ]

    signals = generate_entry_signals(
        close_prices=close_prices,
        upper_band=upper_band,
        lower_band=lower_band,
        squeeze_events=squeeze_events
    )

    # Should only have one BUY signal on day 10
    buy_signals = signals[signals['signal'] == 'BUY']
    assert len(buy_signals[buy_signals.index == dates[10]]) == 1
