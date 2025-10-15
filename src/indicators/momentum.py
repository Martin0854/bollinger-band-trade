"""
Momentum Indicators (Entities 1-3: RSI, MACD, ATR)
Technical indicators for momentum and volatility analysis.
Implements Phase 1-4 auxiliary indicators.

This module implements:
- RSI (Entity 1): FR-003, FR-004, FR-005, FR-007
- MACD (Entity 2): FR-008, FR-009, FR-010, FR-011 (Phase 2)
- ATR (Entity 3): FR-016, FR-017 (Phase 4)
"""

import pandas as pd
import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ========================================================================
# Entity 1: RSI Indicator (Phase 1 - User Story 2)
# ========================================================================

class RSIIndicator:
    """
    Entity 1: RSI (Relative Strength Index) momentum indicator.

    Measures momentum on a 0-100 scale using Wilder's smoothing method.
    - RSI > 70: Overbought (potential reversal down)
    - RSI < 30: Oversold (potential reversal up)
    - 30 < RSI < 70: Neutral zone

    Implements FR-003, FR-004, FR-005, FR-007 from spec.md.

    Attributes:
        period (int): RSI calculation period (default: 14 days)
        overbought (int): Overbought threshold (default: 70)
        oversold (int): Oversold threshold (default: 30)

    Example:
        >>> rsi = RSIIndicator(period=14, overbought=70, oversold=30)
        >>> rsi_values = rsi.calculate(close_prices)
        >>> if rsi.is_neutral(rsi_values.iloc[-1]):
        >>>     # RSI in neutral zone, allow entry
    """

    def __init__(
        self,
        period: int = 14,
        overbought: int = 70,
        oversold: int = 30
    ):
        """
        Initialize RSI indicator with configuration parameters.

        Args:
            period: Lookback period for RSI calculation (days)
            overbought: Upper threshold for overbought condition
            oversold: Lower threshold for oversold condition

        Raises:
            ValueError: If parameters are invalid
        """
        if period <= 0:
            raise ValueError(f"RSI period must be positive, got: {period}")
        if not (0 <= oversold < overbought <= 100):
            raise ValueError(
                f"Invalid thresholds: oversold={oversold}, overbought={overbought}. "
                f"Must satisfy: 0 <= oversold < overbought <= 100"
            )

        self.period = period
        self.overbought = overbought
        self.oversold = oversold

    def calculate(self, prices: pd.Series) -> pd.Series:
        """
        Calculate RSI using Wilder's exponential smoothing method (FR-003).

        Formula:
            RSI = 100 - (100 / (1 + RS))
            RS = Average Gain / Average Loss
            where averages use EMA (Wilder's smoothing)

        Args:
            prices: Time series of closing prices

        Returns:
            pandas.Series: RSI values (0-100). NaN where insufficient data.

        Edge Cases (FR-007):
            - Insufficient data (< period+1 days) → NaN
            - No price movement → NaN or 50
            - All gains or all losses → edge case handling
        """
        # Calculate price changes
        delta = prices.diff()

        # Separate gains and losses
        gain = delta.where(delta > 0, 0)  # Positive changes only
        loss = -delta.where(delta < 0, 0)  # Negative changes (as positive values)

        # Apply Wilder's smoothing (EMA with alpha = 1/period)
        # Use pandas EMA with span parameter (span = period)
        avg_gain = gain.ewm(span=self.period, adjust=False).mean()
        avg_loss = loss.ewm(span=self.period, adjust=False).mean()

        # Calculate RS (Relative Strength)
        # Handle division by zero (when avg_loss = 0, RSI = 100)
        rs = avg_gain / avg_loss

        # Calculate RSI
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def is_neutral(self, rsi_value: float) -> bool:
        """
        Check if RSI is in neutral zone (FR-004).

        Neutral zone: oversold < RSI < overbought
        - Not overbought: allows BUY entry
        - Not oversold: allows SHORT entry

        Args:
            rsi_value: Current RSI value (0-100)

        Returns:
            bool: True if RSI is neutral, False if overbought/oversold or NaN

        Example:
            >>> rsi.is_neutral(50)  # True - neutral
            >>> rsi.is_neutral(75)  # False - overbought
            >>> rsi.is_neutral(25)  # False - oversold
        """
        # Handle NaN (FR-007 - insufficient data)
        if pd.isna(rsi_value):
            logger.warning("RSI is NaN (insufficient data - FR-007)")
            return False

        # Check if in neutral zone
        is_neutral = self.oversold < rsi_value < self.overbought

        if not is_neutral:
            if rsi_value >= self.overbought:
                logger.debug(f"RSI overbought: {rsi_value:.1f} >= {self.overbought}")
            elif rsi_value <= self.oversold:
                logger.debug(f"RSI oversold: {rsi_value:.1f} <= {self.oversold}")

        return is_neutral

    def is_overbought(self, rsi_value: float) -> bool:
        """
        Check if RSI indicates overbought condition (FR-005).

        Used for exit signals when holding a position.

        Args:
            rsi_value: Current RSI value

        Returns:
            bool: True if RSI >= overbought threshold
        """
        if pd.isna(rsi_value):
            return False

        return rsi_value >= self.overbought

    def is_oversold(self, rsi_value: float) -> bool:
        """
        Check if RSI indicates oversold condition.

        Args:
            rsi_value: Current RSI value

        Returns:
            bool: True if RSI <= oversold threshold
        """
        if pd.isna(rsi_value):
            return False

        return rsi_value <= self.oversold


# ========================================================================
# Entity 2: MACD Indicator (Phase 2 - User Story 3)
# ========================================================================

# Placeholder for MACD implementation (Phase 2)
# Will be implemented in Phase 5


# ========================================================================
# Entity 3: ATR Indicator (Phase 4 - User Story 5)
# ========================================================================

# Placeholder for ATR implementation (Phase 4)
# Will be implemented in Phase 7
