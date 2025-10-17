"""Binance data provider for cryptocurrency markets."""

from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd
from binance.client import Client

from src.data.providers.base import MarketDataProvider


class BinanceCryptoProvider(MarketDataProvider):
    """
    Data provider for cryptocurrency pairs via Binance API.

    Fetches OHLCV data for crypto trading pairs (BTC, ETH, etc.) using python-binance.
    Returns timezone-aware UTC timestamps for 24/7 market support.
    No API key required for public market data.
    """

    def __init__(self):
        """Initialize Binance client without API key (public data only)."""
        self.client = Client(api_key=None, api_secret=None)

    def fetch_ohlcv(
        self, symbol: str, start_date: date, end_date: date
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data for given crypto symbol and date range.

        Implements cache-first strategy (T054-T055):
        1. Check Parquet cache for existing data
        2. If cache hit: Return cached data
        3. If cache miss: Fetch from Binance API → Cache → Return

        Args:
            symbol: Crypto trading pair (e.g., 'BTCUSDT', 'ETHUSDT')
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            DataFrame with columns: [Open, High, Low, Close, Volume]
            Index: DatetimeIndex (timezone-aware UTC)
            None if data unavailable or symbol invalid
        """
        import logging
        
        if not self.validate_symbol(symbol):
            return None

        # T054: Check cache first (cache-first strategy)
        from src.data.storage import load_from_parquet
        cached_df = load_from_parquet(
            stock_code=symbol,
            start_date=start_date,
            end_date=end_date,
            market_type='crypto'
        )

        if cached_df is not None:
            logging.debug(f"BinanceCryptoProvider: Cache HIT for {symbol} ({start_date} to {end_date})")
            return cached_df

        # T055: Cache miss - fetch from API
        logging.debug(f"BinanceCryptoProvider: Cache MISS for {symbol} ({start_date} to {end_date}), fetching from API...")

        try:
            # Convert dates to millisecond timestamps for Binance API
            start_ms = int(datetime.combine(start_date, datetime.min.time()).timestamp() * 1000)
            end_ms = int(datetime.combine(end_date + timedelta(days=1), datetime.min.time()).timestamp() * 1000)

            # Fetch daily klines (candlestick data) from Binance
            klines = self.client.get_historical_klines(
                symbol=symbol,
                interval=Client.KLINE_INTERVAL_1DAY,
                start_str=start_ms,
                end_str=end_ms
            )

            if not klines:
                return None

            # Convert to DataFrame
            # Binance klines format: [open_time, open, high, low, close, volume, close_time, ...]
            df = pd.DataFrame(klines, columns=[
                'open_time', 'Open', 'High', 'Low', 'Close', 'Volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])

            # Convert timestamps to datetime (timezone-aware UTC)
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms', utc=True)
            df.set_index('open_time', inplace=True)

            # Validate timezone (T037)
            if df.index.tz is None:
                logging.warning(
                    f"BinanceCryptoProvider: Timezone missing for {symbol} data. "
                    "Expected timezone-aware UTC timestamps for crypto data."
                )
            elif str(df.index.tz) != 'UTC':
                logging.warning(
                    f"BinanceCryptoProvider: Unexpected timezone '{df.index.tz}' for {symbol} data. "
                    "Expected UTC for crypto data."
                )
            else:
                logging.debug(f"BinanceCryptoProvider: Validated UTC timezone for {symbol} data ({len(df)} rows)")

            # Select only OHLCV columns and convert to numeric
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            df = df.astype(float)

            # T055: Save to cache for future runs
            from src.data.storage import save_to_parquet
            cache_path = save_to_parquet(
                df=df,
                stock_code=symbol,
                start_date=start_date,
                end_date=end_date,
                market_type='crypto'
            )
            logging.info(f"BinanceCryptoProvider: Cached {symbol} data to {cache_path}")

            return df

        except Exception as e:
            logging.error(f"BinanceCryptoProvider: Error fetching {symbol}: {e}")
            # Return None on any error (network, invalid symbol, API limits, etc.)
            return None

    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate symbol format for crypto markets.

        Args:
            symbol: Asset identifier to validate

        Returns:
            True if symbol format valid (uppercase)
        """
        return symbol.isupper() and len(symbol) >= 6

    def get_market_type(self) -> str:
        """
        Return market type identifier.

        Returns:
            "crypto"
        """
        return "crypto"
