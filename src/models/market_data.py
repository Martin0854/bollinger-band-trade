"""
MarketData model for managing OHLCV data with indicators.
Wraps pandas DataFrame with validation and indicator storage.
Supports both stock and cryptocurrency markets.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

import pandas as pd

from src.utils.validation import validate_ohlcv_dataframe


@dataclass
class MarketData:
    """
    MarketData wraps OHLCV data with computed indicators.
    Supports both stock and cryptocurrency markets.

    Attributes:
        symbol: Asset identifier (6-digit code for stocks, "BTCUSDT" for crypto)
        market_type: Market type ("stock" or "crypto")
        ohlcv: DataFrame with Open, High, Low, Close, Volume columns
        start_date: First date in dataset
        end_date: Last date in dataset
        bollinger_bands: DataFrame with upper, middle, lower, bandwidth columns
        squeeze_events: List of detected squeeze events
    """
    symbol: str
    market_type: str
    ohlcv: pd.DataFrame
    start_date: date
    end_date: date
    bollinger_bands: Optional[pd.DataFrame] = None
    squeeze_events: list = field(default_factory=list)

    def __post_init__(self):
        """Validate market data."""
        # Validate market_type
        if self.market_type not in ('stock', 'crypto'):
            raise ValueError(
                f"Invalid market_type: '{self.market_type}'. Must be 'stock' or 'crypto'"
            )

        # Validate symbol format based on market type
        if self.market_type == 'stock':
            if not (self.symbol.isdigit() and len(self.symbol) == 6):
                raise ValueError(
                    f"Invalid stock symbol: '{self.symbol}'. "
                    f"Korean stock codes must be exactly 6 digits (e.g., '005930')"
                )
        elif self.market_type == 'crypto':
            if not self.symbol.isupper():
                raise ValueError(
                    f"Invalid crypto symbol: '{self.symbol}'. "
                    f"Crypto symbols must be uppercase (e.g., 'BTCUSDT')"
                )

        # Validate OHLCV data integrity
        validate_ohlcv_dataframe(self.ohlcv, self.symbol)

        # Validate date range
        if self.start_date > self.end_date:
            raise ValueError(
                f"start_date ({self.start_date}) must be <= end_date ({self.end_date})"
            )

    def get_close_prices(self) -> pd.Series:
        """
        Get close prices as Series.

        Returns:
            Series of close prices indexed by date
        """
        return self.ohlcv['Close']

    def get_ohlcv_slice(self, start: date, end: date) -> pd.DataFrame:
        """
        Get OHLCV data for a specific date range.

        Args:
            start: Start date
            end: End date

        Returns:
            DataFrame with OHLCV data in specified range
        """
        return self.ohlcv.loc[start:end]

    def add_bollinger_bands(self, bands: pd.DataFrame) -> None:
        """
        Add computed Bollinger Bands to market data.

        Args:
            bands: DataFrame with upper, middle, lower, bandwidth columns
        """
        required_cols = ['upper', 'middle', 'lower', 'bandwidth']
        if not all(col in bands.columns for col in required_cols):
            raise ValueError(
                f"Bollinger bands must have columns: {required_cols}"
            )

        self.bollinger_bands = bands

    def get_bollinger_at_date(self, target_date: date) -> Optional[dict]:
        """
        Get Bollinger Band values at a specific date.

        Args:
            target_date: Date to retrieve values for

        Returns:
            Dictionary with upper, middle, lower, bandwidth keys, or None if not available
        """
        if self.bollinger_bands is None:
            return None

        if target_date not in self.bollinger_bands.index:
            return None

        row = self.bollinger_bands.loc[target_date]
        return {
            'upper': Decimal(str(row['upper'])),
            'middle': Decimal(str(row['middle'])),
            'lower': Decimal(str(row['lower'])),
            'bandwidth': Decimal(str(row['bandwidth']))
        }

    def add_squeeze_event(self, event: dict) -> None:
        """
        Add a detected squeeze event.

        Args:
            event: Dictionary with squeeze event details
        """
        self.squeeze_events.append(event)

    def get_squeeze_events_in_range(self, start: date, end: date) -> list:
        """
        Get squeeze events within a date range.

        Args:
            start: Start date
            end: End date

        Returns:
            List of squeeze events in specified range
        """
        return [
            event for event in self.squeeze_events
            if start <= event.get('detection_date', start) <= end
        ]

    def has_sufficient_data_for_period(self, period: int) -> bool:
        """
        Check if dataset has enough data for a given period calculation.

        Args:
            period: Required number of data points

        Returns:
            True if dataset has >= period rows
        """
        return len(self.ohlcv) >= period

    def get_latest_close_price(self) -> Decimal:
        """
        Get the most recent closing price.

        Returns:
            Latest close price as Decimal
        """
        return Decimal(str(self.ohlcv['Close'].iloc[-1]))

    def get_price_at_date(self, target_date: date) -> Optional[Decimal]:
        """
        Get closing price at a specific date.

        Args:
            target_date: Date to retrieve price for

        Returns:
            Close price as Decimal, or None if date not found
        """
        if target_date not in self.ohlcv.index:
            return None

        return Decimal(str(self.ohlcv.loc[target_date, 'Close']))

    def to_dict(self) -> dict:
        """
        Convert MarketData to dictionary representation.

        Returns:
            Dictionary with market data summary
        """
        return {
            'symbol': self.symbol,
            'market_type': self.market_type,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'num_data_points': len(self.ohlcv),
            'has_bollinger_bands': self.bollinger_bands is not None,
            'num_squeeze_events': len(self.squeeze_events),
            'latest_close': float(self.get_latest_close_price())
        }
