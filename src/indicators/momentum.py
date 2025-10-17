"""
Momentum Indicators (Entities 1-3: RSI, MACD, ATR)
Technical indicators for momentum and volatility analysis.
Implements Phase 1-4 auxiliary indicators.

This module implements:
- RSI (Entity 1): FR-003, FR-004, FR-005, FR-007
- MACD (Entity 2): FR-008, FR-009, FR-010, FR-011 (Phase 2)
- ATR (Entity 3): FR-016, FR-017 (Phase 4)
"""

import logging

import pandas as pd

from src.utils.logging import log_atr_stop_loss

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

class MACDIndicator:
    """
    Entity 2: MACD (Moving Average Convergence Divergence) trend indicator.

    Detects trend direction and momentum using the difference between
    fast and slow EMAs:
    - MACD > Signal: Bullish (golden cross, uptrend)
    - MACD < Signal: Bearish (death cross, downtrend)
    - Histogram > 0: Momentum increasing
    - Histogram < 0: Momentum decreasing

    Implements FR-008, FR-009, FR-010, FR-011 from spec.md.

    Attributes:
        fast_period (int): Fast EMA period (default: 12 days)
        slow_period (int): Slow EMA period (default: 26 days)
        signal_period (int): Signal line EMA period (default: 9 days)

    Example:
        >>> macd = MACDIndicator(fast_period=12, slow_period=26, signal_period=9)
        >>> result = macd.calculate(close_prices)
        >>> if macd.is_bullish(result['macd'].iloc[-1], result['signal'].iloc[-1]):
        >>>     # MACD bullish, allow entry
    """

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ):
        """
        Initialize MACD indicator with configuration parameters.

        Args:
            fast_period: Fast EMA period (days)
            slow_period: Slow EMA period (days)
            signal_period: Signal line EMA period (days)

        Raises:
            ValueError: If parameters are invalid
        """
        if fast_period <= 0:
            raise ValueError(f"MACD fast_period must be positive, got: {fast_period}")
        if slow_period <= 0:
            raise ValueError(f"MACD slow_period must be positive, got: {slow_period}")
        if signal_period <= 0:
            raise ValueError(f"MACD signal_period must be positive, got: {signal_period}")
        if slow_period <= fast_period:
            raise ValueError(
                f"MACD slow_period ({slow_period}) must be > fast_period ({fast_period})"
            )

        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

    def calculate(self, prices: pd.Series) -> pd.DataFrame:
        """
        Calculate MACD, signal line, and histogram (FR-008).

        Formula:
            MACD Line = EMA(fast_period) - EMA(slow_period)
            Signal Line = EMA(MACD Line, signal_period)
            Histogram = MACD Line - Signal Line

        Args:
            prices: Time series of closing prices

        Returns:
            DataFrame with columns: macd, signal, histogram
            NaN values where insufficient data.

        Edge Cases (FR-011):
            - Insufficient data (< slow_period days) → NaN for early values
            - EMA calculation requires warmup period
        """
        # Calculate fast and slow EMAs
        ema_fast = prices.ewm(span=self.fast_period, adjust=False).mean()
        ema_slow = prices.ewm(span=self.slow_period, adjust=False).mean()

        # MACD line = fast EMA - slow EMA
        macd_line = ema_fast - ema_slow

        # Signal line = EMA of MACD line
        signal_line = macd_line.ewm(span=self.signal_period, adjust=False).mean()

        # Histogram = MACD line - signal line
        histogram = macd_line - signal_line

        # Return as DataFrame
        return pd.DataFrame({
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        })

    def is_bullish(self, macd: float, signal: float) -> bool:
        """
        Check if MACD indicates bullish trend (FR-009).

        Bullish condition: MACD line > signal line (golden cross)
        - Indicates upward momentum
        - Confirms breakout validity

        Args:
            macd: Current MACD line value
            signal: Current signal line value

        Returns:
            bool: True if MACD > signal (bullish), False otherwise

        Example:
            >>> macd.is_bullish(5.0, 3.0)  # True - bullish
            >>> macd.is_bullish(2.0, 4.0)  # False - bearish
        """
        # Handle NaN (FR-011 - insufficient data)
        if pd.isna(macd) or pd.isna(signal):
            logger.warning("MACD is NaN (insufficient data - FR-011)")
            return False

        # Check if MACD above signal (bullish)
        is_bullish = macd > signal

        if not is_bullish:
            logger.debug(f"MACD bearish: {macd:.2f} <= {signal:.2f}")

        return is_bullish

    def is_bearish(self, macd: float, signal: float) -> bool:
        """
        Check if MACD indicates bearish trend (FR-010).

        Bearish condition: MACD line < signal line (death cross)
        - Indicates downward momentum
        - Used for exit signals

        Args:
            macd: Current MACD line value
            signal: Current signal line value

        Returns:
            bool: True if MACD < signal (bearish), False otherwise
        """
        # Handle NaN
        if pd.isna(macd) or pd.isna(signal):
            return False

        return macd < signal


# ========================================================================
# Entity 3: ATR Indicator (Phase 4 - User Story 5)
# ========================================================================

class ATRIndicator:
    """
    Entity 3: ATR (Average True Range) volatility indicator.

    Measures market volatility using the true range of price movement.
    Used for dynamic stop-loss calculation that adapts to market conditions.
    - High ATR: High volatility → wider stop-loss
    - Low ATR: Low volatility → tighter stop-loss

    Implements FR-016, FR-017 from spec.md.

    Attributes:
        period (int): ATR calculation period (default: 14 days)
        multiplier (float): Stop-loss distance multiplier (default: 2.0)

    Example:
        >>> atr = ATRIndicator(period=14, multiplier=2.0)
        >>> atr_values = atr.calculate(high, low, close)
        >>> stop_loss = atr.calculate_stop_loss(entry_price=60000, atr_value=atr_values.iloc[-1])
    """

    def __init__(
        self,
        period: int = 14,
        multiplier: float = 2.0
    ):
        """
        Initialize ATR indicator with configuration parameters.

        Args:
            period: Lookback period for ATR calculation (days)
            multiplier: Stop-loss distance multiplier (ATR * multiplier)

        Raises:
            ValueError: If parameters are invalid
        """
        if period <= 0:
            raise ValueError(f"ATR period must be positive, got: {period}")
        if multiplier <= 0:
            raise ValueError(f"ATR multiplier must be positive, got: {multiplier}")

        self.period = period
        self.multiplier = multiplier

    def calculate(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series
    ) -> pd.Series:
        """
        Calculate ATR using Wilder's smoothing method (FR-016).

        True Range is the maximum of:
        1. Current High - Current Low
        2. abs(Current High - Previous Close)
        3. abs(Current Low - Previous Close)

        ATR = EMA(True Range, period)

        Args:
            high: Time series of high prices
            low: Time series of low prices
            close: Time series of closing prices

        Returns:
            pandas.Series: ATR values. NaN where insufficient data.

        Edge Cases:
            - Insufficient data (< 2 days) → NaN
            - First value always NaN (no previous close)
        """
        # Calculate true range components
        # TR1: Current high - current low
        tr1 = high - low

        # TR2: abs(current high - previous close)
        prev_close = close.shift(1)
        tr2 = (high - prev_close).abs()

        # TR3: abs(current low - previous close)
        tr3 = (low - prev_close).abs()

        # True range is the maximum of the three
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Apply Wilder's smoothing (EMA with span=period)
        atr = true_range.ewm(span=self.period, adjust=False).mean()

        return atr

    def calculate_stop_loss(
        self,
        entry_price: float,
        atr_value: float,
        stock_code: str = ""
    ) -> float:
        """
        Calculate dynamic stop-loss based on ATR (FR-017).

        Formula:
            Stop Loss = Entry Price - (ATR * multiplier)

        Args:
            entry_price: Position entry price
            atr_value: Current ATR value
            stock_code: Stock code for logging (optional)

        Returns:
            float: Stop-loss price

        Note:
            Stop-loss can be negative if ATR is very high relative to price.
            This indicates extremely high volatility and immediate exit should be considered.
        """
        stop_loss = entry_price - (atr_value * self.multiplier)

        # Log ATR stop-loss calculation with structured fields (T067)
        if stock_code:
            log_atr_stop_loss(
                logger,
                stock_code,
                entry_price,
                atr_value,
                stop_loss,
                self.multiplier
            )

        return stop_loss
