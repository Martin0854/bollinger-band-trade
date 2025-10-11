"""
Signal generation for entry and exit signals.
Implements squeeze-based entry logic and band-touch exit logic.
"""

import pandas as pd
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict
from dataclasses import dataclass
import pytz
import uuid


@dataclass(frozen=True)
class Signal:
    """
    Represents a trading signal (BUY/SELL/HOLD).

    Attributes:
        date: Signal generation date
        stock_code: 6-digit stock code
        signal_type: BUY, SELL, or HOLD
        reason: Why signal was generated
        price: Price at signal generation
        bollinger_values: Dict with upper, middle, lower
    """
    date: datetime
    stock_code: str
    signal_type: str
    reason: str
    price: Decimal
    bollinger_values: Dict[str, Decimal]

    def __post_init__(self):
        """Validate signal fields."""
        # Validate stock_code
        if not (self.stock_code.isdigit() and len(self.stock_code) == 6):
            raise ValueError(f"Invalid stock_code: {self.stock_code}")

        # Validate price
        if self.price <= 0:
            raise ValueError(f"Price must be positive: {self.price}")

    def to_log_dict(self) -> Dict:
        """Convert to JSON-serializable dict."""
        return {
            'date': self.date.isoformat(),
            'stock_code': self.stock_code,
            'signal': self.signal_type.lower(),
            'reason': self.reason,
            'price': float(self.price),
            'bollinger_upper': float(self.bollinger_values.get('upper', 0)),
            'bollinger_middle': float(self.bollinger_values.get('middle', 0)),
            'bollinger_lower': float(self.bollinger_values.get('lower', 0))
        }


def generate_entry_signals(
    close_prices: pd.Series,
    upper_band: pd.Series,
    lower_band: pd.Series,
    squeeze_events: list,
    allow_shorts: bool = False
) -> pd.DataFrame:
    """
    Generate entry signals based on squeeze expansion.

    Args:
        close_prices: Series of closing prices
        upper_band: Upper Bollinger Band
        lower_band: Lower Bollinger Band
        squeeze_events: List of detected squeeze events with expansion confirmation
        allow_shorts: Whether to generate SHORT signals (default False)

    Returns:
        DataFrame with columns: signal, reason
    """
    # Initialize all signals as HOLD
    signals = pd.DataFrame(index=close_prices.index)
    signals['signal'] = 'HOLD'
    signals['reason'] = ''

    # Process each squeeze event
    for event in squeeze_events:
        if not event.get('expansion_confirmed'):
            continue

        detection_date = event['detection_date']
        direction_bias = event.get('direction_bias')

        # Find dates after detection where expansion occurs
        later_dates = close_prices.index > detection_date
        if not later_dates.any():
            continue

        # Check for breakout in direction of bias
        for date in close_prices.index[later_dates]:
            price = close_prices.loc[date]
            upper = upper_band.loc[date]
            lower = lower_band.loc[date]

            # BUY signal: price breaks above upper band with lower bias
            if direction_bias == 'upper' and price > upper:
                signals.loc[date, 'signal'] = 'BUY'
                signals.loc[date, 'reason'] = 'squeeze_expansion_buy'
                break

            # SHORT signal: price breaks below lower band with upper bias
            # (only if shorts allowed)
            if direction_bias == 'lower' and price < lower and allow_shorts:
                signals.loc[date, 'signal'] = 'SHORT'
                signals.loc[date, 'reason'] = 'squeeze_expansion_short'
                break

    return signals


def generate_exit_signals(
    close_prices: pd.Series,
    upper_band: pd.Series,
    middle_band: pd.Series,
    position_entry_date: datetime
) -> pd.DataFrame:
    """
    Generate exit signals based on band touches.

    Args:
        close_prices: Series of closing prices
        upper_band: Upper Bollinger Band
        middle_band: Middle Bollinger Band
        position_entry_date: When position was entered

    Returns:
        DataFrame with columns: signal, reason
    """
    # Initialize all signals as HOLD
    signals = pd.DataFrame(index=close_prices.index)
    signals['signal'] = 'HOLD'
    signals['reason'] = ''

    # Only generate signals after entry
    after_entry = close_prices.index > position_entry_date

    for date in close_prices.index[after_entry]:
        price = close_prices.loc[date]
        upper = upper_band.loc[date]
        middle = middle_band.loc[date]

        # Exit at upper band (profit target)
        if price >= upper:
            signals.loc[date, 'signal'] = 'SELL'
            signals.loc[date, 'reason'] = 'band_upper_exit'
            break

        # Exit below middle band (stop loss alternative)
        if price < middle:
            signals.loc[date, 'signal'] = 'SELL'
            signals.loc[date, 'reason'] = 'band_middle_cross'
            break

    return signals
