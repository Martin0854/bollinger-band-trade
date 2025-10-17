"""Abstract base class for market data providers."""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

import pandas as pd


class MarketDataProvider(ABC):
    """Abstract interface for fetching market data from different sources.

    This interface defines the contract that all market data providers
    (stocks, crypto, etc.) must implement.
    """

    @abstractmethod
    def fetch_ohlcv(
        self, symbol: str, start_date: date, end_date: date
    ) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data for given symbol and date range.

        Args:
            symbol: Asset identifier (6-digit code for stocks, "BTCUSDT" for crypto)
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            DataFrame with columns: [Open, High, Low, Close, Volume]
            Index: DatetimeIndex (timezone-aware for crypto, naive for stocks)
            None if data unavailable
        """
        pass

    @abstractmethod
    def validate_symbol(self, symbol: str) -> bool:
        """Validate symbol format for this market type.

        Args:
            symbol: Asset identifier to validate

        Returns:
            True if symbol format valid for this provider's market
        """
        pass

    @abstractmethod
    def get_market_type(self) -> str:
        """Return market type identifier.

        Returns:
            "stock" or "crypto"
        """
        pass
