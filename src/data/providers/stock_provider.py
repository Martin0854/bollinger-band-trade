"""Yahoo Finance data provider for Korean stock market."""

from datetime import date
from typing import Optional

import pandas as pd
import yfinance as yf

from src.data.providers.base import MarketDataProvider


class YahooFinanceStockProvider(MarketDataProvider):
    """
    Data provider for Korean stocks via Yahoo Finance.

    Fetches OHLCV data for Korean stocks (KOSPI/KOSDAQ) using yfinance library.
    Automatically appends exchange suffixes (.KS for KOSPI, .KQ for KOSDAQ).
    """

    def fetch_ohlcv(
        self, symbol: str, start_date: date, end_date: date
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data for given stock symbol and date range.

        Args:
            symbol: 6-digit Korean stock code (e.g., '005930' for Samsung)
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            DataFrame with columns: [Open, High, Low, Close, Volume]
            Index: DatetimeIndex (timezone-naive)
            None if data unavailable or symbol invalid
        """
        if not self.validate_symbol(symbol):
            return None

        # Append exchange suffix for Yahoo Finance
        # Try KOSPI first (.KS), then KOSDAQ (.KQ)
        yahoo_symbol = f"{symbol}.KS"

        try:
            # Download data from Yahoo Finance
            ticker = yf.Ticker(yahoo_symbol)
            df = ticker.history(
                start=start_date.isoformat(),
                end=end_date.isoformat(),
                auto_adjust=False,  # Keep raw OHLC prices
                actions=False  # Don't include dividends/splits
            )

            # If no data returned, try KOSDAQ exchange
            if df.empty:
                yahoo_symbol = f"{symbol}.KQ"
                ticker = yf.Ticker(yahoo_symbol)
                df = ticker.history(
                    start=start_date.isoformat(),
                    end=end_date.isoformat(),
                    auto_adjust=False,
                    actions=False
                )

            if df.empty:
                return None

            # Select only OHLCV columns
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]

            # Ensure timezone-naive index (yfinance returns timezone-aware)
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)

            return df

        except Exception:
            # Return None on any error (network, invalid symbol, etc.)
            return None

    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate symbol format for Korean stock market.

        Args:
            symbol: Asset identifier to validate

        Returns:
            True if symbol format valid (6 digits)
        """
        return symbol.isdigit() and len(symbol) == 6

    def get_market_type(self) -> str:
        """
        Return market type identifier.

        Returns:
            "stock"
        """
        return "stock"
