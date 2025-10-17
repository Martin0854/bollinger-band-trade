"""
Signal generation for entry and exit signals.
Implements squeeze-based entry logic and band-touch exit logic.
Enhanced with auxiliary indicator filters (Phase 1-4).
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional

import pandas as pd

from src.utils.logging import log_confidence_score, log_filter_result

logger = logging.getLogger(__name__)


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


# ========================================================================
# Enhanced Signal Generator (Phase 1-4)
# Integrates auxiliary indicator filters with confidence scoring
# ========================================================================

class EnhancedSignalGenerator:
    """
    Enhanced signal generator with auxiliary indicator filters.

    Integrates Volume, RSI, MACD filters with confidence scoring
    to reduce false signals and improve win rate.

    Attributes:
        volume_filter: Optional VolumeFilter instance
        rsi_indicator: Optional RSIIndicator instance
        macd_indicator: Optional MACDIndicator instance
        confidence: SignalConfidence instance for scoring and threshold checking
        confidence_threshold: Minimum confidence score (kept for backward compatibility)
    """

    def __init__(
        self,
        volume_filter: Optional['VolumeFilter'] = None,
        rsi_indicator: Optional['RSIIndicator'] = None,
        macd_indicator: Optional['MACDIndicator'] = None,
        confidence_threshold: int = 60,
        confidence_scoring: Optional[Dict[str, int]] = None
    ):
        """
        Initialize enhanced signal generator with optional filters.

        Args:
            volume_filter: VolumeFilter instance (Phase 1)
            rsi_indicator: RSIIndicator instance (Phase 1)
            macd_indicator: MACDIndicator instance (Phase 2)
            confidence_threshold: Minimum confidence score for entry (Phase 3)
            confidence_scoring: Optional custom scoring weights (Phase 3)
        """
        from src.signals.confidence import SignalConfidence

        self.volume_filter = volume_filter
        self.rsi_indicator = rsi_indicator
        self.macd_indicator = macd_indicator

        # Initialize SignalConfidence with threshold and optional custom scoring
        self.confidence = SignalConfidence(
            threshold=confidence_threshold,
            scoring=confidence_scoring
        )

        # Keep for backward compatibility
        self.confidence_threshold = confidence_threshold

    def check_volume_condition(
        self,
        current_volume: float,
        avg_volume: float,
        stock_code: str = ""
    ) -> bool:
        """
        Check if volume condition is met (FR-002, FR-006).

        Returns True if:
        - Volume filter is disabled, OR
        - Volume filter passes (volume >= avg * multiplier)

        Returns False if volume data is missing or filter fails.
        """
        if self.volume_filter is None:
            # Filter disabled - allow signal
            return True

        # Check volume spike
        passes = self.volume_filter.check_volume_spike(current_volume, avg_volume)

        # Log filter result with structured logging (T067)
        multiplier = self.volume_filter.multiplier if self.volume_filter else 1.5
        log_filter_result(
            logger,
            "Volume",
            stock_code,
            passes,
            reason=f"volume {'≥' if passes else '<'} {multiplier}x average",
            current_volume=current_volume,
            avg_volume=avg_volume,
            multiplier=multiplier
        )

        return passes

    def check_rsi_condition(self, rsi_value: Optional[float], stock_code: str = "") -> bool:
        """
        Check if RSI condition is met (FR-004, FR-007).

        Returns True if:
        - RSI indicator is disabled, OR
        - RSI is in neutral zone (oversold < RSI < overbought)

        Returns False if RSI data is missing or overbought.
        """
        if self.rsi_indicator is None:
            # Filter disabled - allow signal
            return True

        if rsi_value is None or pd.isna(rsi_value):
            # Insufficient data (FR-007) - skip filter
            logger.warning(
                "RSI filter skipped: insufficient data (FR-007)",
                extra={'stock_code': stock_code, 'filter': 'RSI'}
            )
            return False

        # Check if RSI is neutral (not overbought/oversold)
        is_neutral = self.rsi_indicator.is_neutral(rsi_value)

        # Determine reason for pass/fail
        if rsi_value >= self.rsi_indicator.overbought:
            reason = "overbought"
        elif rsi_value <= self.rsi_indicator.oversold:
            reason = "oversold"
        else:
            reason = "neutral zone"

        # Log filter result with structured logging (T067)
        log_filter_result(
            logger,
            "RSI",
            stock_code,
            is_neutral,
            reason=reason,
            rsi_value=rsi_value,
            overbought=self.rsi_indicator.overbought,
            oversold=self.rsi_indicator.oversold
        )

        return is_neutral

    def check_macd_condition(self, macd_histogram: Optional[float], stock_code: str = "") -> bool:
        """
        Check if MACD condition is met (FR-009, FR-011).

        Returns True if:
        - MACD indicator is disabled, OR
        - MACD histogram > 0 (bullish trend confirmed)

        Returns False if MACD data is missing or bearish.

        Args:
            macd_histogram: Current MACD histogram value (macd_line - signal_line)

        Returns:
            bool: True if MACD condition met, False otherwise
        """
        if self.macd_indicator is None:
            # Filter disabled - allow signal
            return True

        if macd_histogram is None or pd.isna(macd_histogram):
            # Insufficient data (FR-011) - skip filter
            logger.warning(
                "MACD filter skipped: insufficient data (FR-011)",
                extra={'stock_code': stock_code, 'filter': 'MACD'}
            )
            return False

        # Check if MACD is bullish (histogram > 0)
        is_bullish = macd_histogram > 0

        # Log filter result with structured logging (T067)
        log_filter_result(
            logger,
            "MACD",
            stock_code,
            is_bullish,
            reason="bullish" if is_bullish else "bearish",
            macd_histogram=macd_histogram
        )

        return is_bullish

    def calculate_confidence_score(
        self,
        volume_pass: bool,
        rsi_pass: bool,
        macd_pass: bool
    ) -> int:
        """
        Calculate signal confidence score (0-100 points).

        Now delegates to SignalConfidence class for flexible scoring.

        Args:
            volume_pass: Volume filter passed
            rsi_pass: RSI filter passed
            macd_pass: MACD filter passed

        Returns:
            int: Confidence score (0-100)
        """
        return self.confidence.calculate_score(volume_pass, rsi_pass, macd_pass)

    def generate_enhanced_signal(
        self,
        date: datetime,
        stock_code: str,
        signal_type: str,
        reason: str,
        price: Decimal,
        bollinger_values: Dict[str, Decimal],
        current_volume: Optional[float] = None,
        avg_volume: Optional[float] = None,
        rsi_value: Optional[float] = None,
        macd_value: Optional[float] = None
    ) -> Optional['EnhancedSignal']:
        """
        Generate enhanced signal with filter checks and confidence scoring.

        Returns None if filters fail or confidence below threshold.
        Returns EnhancedSignal if all conditions met.

        Args:
            date: Signal date
            stock_code: 6-digit stock code
            signal_type: BUY or SELL
            reason: Signal reason
            price: Signal price
            bollinger_values: Bollinger band values
            current_volume: Current volume (for filter)
            avg_volume: Average volume (for filter)
            rsi_value: Current RSI value (for filter)
            macd_value: Current MACD histogram (for filter)

        Returns:
            EnhancedSignal if conditions met, None otherwise
        """
        from src.models.trade import EnhancedSignal

        # Check volume condition (FR-002, FR-006)
        # If filter is disabled (None), treat as passing
        if self.volume_filter is None:
            volume_pass = True
        elif current_volume is not None and avg_volume is not None:
            volume_pass = self.check_volume_condition(current_volume, avg_volume, stock_code)
            if not volume_pass:
                # Volume filter enabled and failed
                return None
        else:
            # Volume filter enabled but data missing
            volume_pass = False

        # Check RSI condition (FR-004, FR-007)
        # If filter is disabled (None), treat as passing
        if self.rsi_indicator is None:
            rsi_pass = True
        elif rsi_value is not None:
            rsi_pass = self.check_rsi_condition(rsi_value, stock_code)
            if not rsi_pass:
                # RSI filter enabled and failed
                return None
        else:
            # RSI filter enabled but data missing
            rsi_pass = False

        # Check MACD condition (FR-009, FR-011) - Phase 2
        # If filter is disabled (None), treat as passing
        if self.macd_indicator is None:
            macd_pass = True
        elif macd_value is not None:
            macd_pass = self.check_macd_condition(macd_value, stock_code)
            if not macd_pass:
                # MACD filter enabled and failed
                return None
        else:
            # MACD filter enabled but data missing
            macd_pass = False

        # Calculate confidence score
        confidence_score = self.calculate_confidence_score(
            volume_pass, rsi_pass, macd_pass
        )

        # Check confidence threshold using SignalConfidence class (with structured logging - T067)
        meets_threshold = self.confidence.meets_threshold(confidence_score)
        log_confidence_score(
            logger,
            stock_code,
            confidence_score,
            self.confidence.threshold,
            volume_pass,
            rsi_pass,
            macd_pass,
            meets_threshold
        )

        if not meets_threshold:
            return None

        # Create enhanced signal
        enhanced_signal = EnhancedSignal(
            stock_code=stock_code,
            signal_type=signal_type,
            execution_price=price,
            execution_timestamp=date,
            reason=reason,
            bollinger_values=bollinger_values,
            confidence_score=confidence_score,
            volume_pass=volume_pass,
            rsi_pass=rsi_pass,
            macd_pass=macd_pass,
            rsi_value=rsi_value,
            macd_value=macd_value,
            atr_value=None,  # Phase 4
            dynamic_stop_loss=None  # Phase 4
        )

        # Log signal generation with structured fields (T067)
        logger.info(
            f"Enhanced signal generated: {signal_type} {stock_code} @ {price}",
            extra={
                'stock_code': stock_code,
                'signal_type': signal_type,
                'price': float(price),
                'confidence_score': confidence_score,
                'volume_pass': volume_pass,
                'rsi_pass': rsi_pass,
                'macd_pass': macd_pass,
                'rsi_value': rsi_value,
                'macd_value': macd_value,
                'reason': reason
            }
        )

        return enhanced_signal
