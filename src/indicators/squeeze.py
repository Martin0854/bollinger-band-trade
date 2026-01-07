"""
Squeeze detection for Bollinger Bands (data-model.md Entity 6).
Detects volatility contractions and direction bias.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

import pandas as pd


class DirectionBias(str, Enum):
    """Direction bias during squeeze period."""
    BULLISH = "bullish"    # Price touched lower band
    BEARISH = "bearish"    # Price touched upper band
    NEUTRAL = "neutral"    # No clear direction


@dataclass
class SqueezeEvent:
    """
    Represents a detected Bollinger Band squeeze event.

    Attributes:
        stock_code: 6-digit Korean stock code
        detection_date: When squeeze was first detected
        band_width_at_detection: Current band width when detected
        band_width_N_days_ago: Band width at lookback start
        lookback_days: Comparison window (e.g., 10)
        threshold_percent: Configured threshold (e.g., 30%)
        direction_bias: Which band price touched (BULLISH/BEARISH/NEUTRAL)
        event_id: Unique identifier
        expansion_confirmed_date: When bands started expanding (optional)
    """
    stock_code: str
    detection_date: datetime
    band_width_at_detection: Decimal
    band_width_N_days_ago: Decimal
    lookback_days: int
    threshold_percent: Decimal
    direction_bias: Optional[str] = None
    event_id: str = None
    expansion_confirmed_date: Optional[datetime] = None

    def __post_init__(self):
        """Generate event_id if not provided."""
        if self.event_id is None:
            object.__setattr__(self, 'event_id', str(uuid.uuid4()))

    @property
    def width_decrease_pct(self) -> Decimal:
        """Calculate percentage decrease in band width."""
        if self.band_width_N_days_ago == 0:
            return Decimal('0')

        decrease = ((self.band_width_N_days_ago - self.band_width_at_detection) /
                   self.band_width_N_days_ago) * 100
        return decrease

    def to_log_dict(self) -> dict:
        """Convert to JSON-serializable dict for logging."""
        return {
            'event_id': self.event_id,
            'stock_code': self.stock_code,
            'detection_date': self.detection_date.isoformat(),
            'band_width_at_detection': float(self.band_width_at_detection),
            'band_width_N_days_ago': float(self.band_width_N_days_ago),
            'width_decrease_pct': float(self.width_decrease_pct),
            'lookback_days': self.lookback_days,
            'threshold_pct': float(self.threshold_percent),
            'direction_bias': self.direction_bias,
            'expansion_confirmed': self.expansion_confirmed_date is not None
        }


def detect_squeeze(
    band_width: pd.Series,
    lookback_days: int,
    threshold_percent: float
) -> pd.Series:
    """
    Detect squeeze events based on band width decrease.

    A squeeze is detected when band width decreases by threshold_percent
    over lookback_days period.

    Args:
        band_width: Series of Bollinger Band widths indexed by date
        lookback_days: Number of days to look back for comparison
        threshold_percent: Minimum decrease percentage to trigger (e.g., 30)

    Returns:
        Boolean Series indicating squeeze detection at each date

    Raises:
        ValueError: If lookback_days <= 0 or threshold_percent out of range
    """
    # Validation
    if lookback_days <= 0:
        raise ValueError(f"lookback_days must be positive, got: {lookback_days}")

    if not (0 <= threshold_percent <= 100):
        raise ValueError(
            f"threshold_percent must be in [0, 100], got: {threshold_percent}"
        )

    # Get band width from N days ago
    band_width_past = band_width.shift(lookback_days)

    # Calculate percentage decrease
    width_decrease_pct = ((band_width_past - band_width) / band_width_past) * 100

    # Squeeze detected when decrease >= threshold
    squeeze_detected = width_decrease_pct >= threshold_percent

    # First lookback_days rows will be False (insufficient history)
    squeeze_detected.iloc[:lookback_days] = False

    return squeeze_detected


def determine_direction_bias(
    close_prices: pd.Series,
    upper_band: pd.Series,
    lower_band: pd.Series,
    squeeze_start_idx: int,
    squeeze_end_idx: int,
    band_touch_tolerance: float = 0.001
) -> Optional[str]:
    """
    Determine direction bias during squeeze period.

    Args:
        close_prices: Series of closing prices
        upper_band: Series of upper Bollinger Band values
        lower_band: Series of lower Bollinger Band values
        squeeze_start_idx: Start index of squeeze period
        squeeze_end_idx: End index of squeeze period
        band_touch_tolerance: Tolerance for band touch detection (default 0.001 = 0.1%)

    Returns:
        "upper" if price touched upper band, "lower" if touched lower band,
        None if no clear touch
    """
    # Get data for squeeze period
    period_closes = close_prices.iloc[squeeze_start_idx:squeeze_end_idx + 1]
    period_upper = upper_band.iloc[squeeze_start_idx:squeeze_end_idx + 1]
    period_lower = lower_band.iloc[squeeze_start_idx:squeeze_end_idx + 1]

    # Check for band touches (configurable tolerance)
    upper_touches = (period_closes >= period_upper * (1 - band_touch_tolerance)).any()
    lower_touches = (period_closes <= period_lower * (1 + band_touch_tolerance)).any()

    if lower_touches and not upper_touches:
        return "lower"
    elif upper_touches and not lower_touches:
        return "upper"
    else:
        return None


def confirm_expansion(
    band_width: pd.Series,
    squeeze_end_date: datetime,
    expansion_threshold_percent: float = 20.0
) -> bool:
    """
    Check if band width has expanded after squeeze.

    Args:
        band_width: Series of band widths
        squeeze_end_date: Date when squeeze ended
        expansion_threshold_percent: Minimum increase to confirm expansion

    Returns:
        True if expansion confirmed, False otherwise
    """
    if squeeze_end_date not in band_width.index:
        return False

    # Get band width at squeeze end
    squeeze_width = band_width.loc[squeeze_end_date]

    # Get subsequent widths
    later_dates = band_width.index > squeeze_end_date
    if not later_dates.any():
        return False

    later_widths = band_width.loc[later_dates]

    # Check if any subsequent width increased by threshold
    width_increases = ((later_widths - squeeze_width) / squeeze_width) * 100
    expansion_confirmed = (width_increases >= expansion_threshold_percent).any()

    return expansion_confirmed
