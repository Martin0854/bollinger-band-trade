"""
Stock universe scanner for daily trading signals.
Fetches data from yfinance and calculates technical indicators.
"""

import warnings
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

from src.signals.sell_strategy import SellStrategyConfig, evaluate_sell_conditions
from src.wizard.portfolio_manager import WizardPosition

warnings.filterwarnings("ignore")


@dataclass
class StockSignal:
    """Signal information for a stock."""

    stock_code: str
    stock_name: str  # Company name
    signal_type: str  # "BUY", "SELL", "HOLD"
    confidence_score: int
    current_price: float
    reason: str
    indicators: Dict[str, float]


def get_stock_name(stock_code: str) -> str:
    """
    Get Korean stock name from local mapping file.

    Args:
        stock_code: 6-digit Korean stock code

    Returns:
        Korean stock name or stock code if not found
    """
    import json

    # Try to load Korean names from local file
    possible_paths = [
        Path("data/stock_names_kr.json"),
        Path(__file__).parent.parent.parent / "data" / "stock_names_kr.json",
    ]

    for path in possible_paths:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    names = json.load(f)
                if stock_code in names:
                    return names[stock_code]
            except Exception:
                pass

    # Fallback to yfinance if not in local mapping
    try:
        ticker = yf.Ticker(f"{stock_code}.KS")
        info = ticker.info
        name = info.get("shortName") or info.get("longName")
        if name:
            return name
        ticker = yf.Ticker(f"{stock_code}.KQ")
        info = ticker.info
        return info.get("shortName") or info.get("longName") or stock_code
    except Exception:
        return stock_code


def load_kospi_top100(filepath: str = "kospi_top100.txt") -> List[str]:
    """Load KOSPI Top 100 stock codes from file."""
    # Try multiple possible locations
    possible_paths = [
        Path(filepath),
        Path("data") / filepath,
        Path(__file__).parent.parent.parent / filepath,
        Path(__file__).parent.parent.parent / "data" / filepath,
    ]

    for path in possible_paths:
        if path.exists():
            with open(path, "r") as f:
                stocks = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            return [s for s in stocks if s][:100]

    raise FileNotFoundError(f"Could not find {filepath} in any expected location")


def fetch_stock_data(stock_code: str, days: int = 60) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV data from Yahoo Finance.

    Args:
        stock_code: 6-digit Korean stock code
        days: Number of days of history to fetch

    Returns:
        DataFrame with OHLCV data or None if fetch failed
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days + 30)  # Extra days for indicator warmup

    ticker = f"{stock_code}.KS"
    try:
        df = yf.download(
            ticker,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            progress=False,
            auto_adjust=False,
        )

        if df.empty:
            # Try KOSDAQ
            ticker = f"{stock_code}.KQ"
            df = yf.download(
                ticker,
                start=start_date.isoformat(),
                end=end_date.isoformat(),
                progress=False,
                auto_adjust=False,
            )

        if df.empty or len(df) < 30:
            return None

        # Handle MultiIndex columns from yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        return df[["Open", "High", "Low", "Close", "Volume"]].dropna()

    except Exception:
        return None


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all technical indicators needed for signal generation.

    Args:
        df: DataFrame with OHLCV data

    Returns:
        DataFrame with added indicator columns
    """
    close = df["Close"].copy()
    volume = df["Volume"].copy()

    # Bollinger Bands (20-day, 2 std dev)
    sma = close.rolling(window=20).mean()
    std = close.rolling(window=20).std()
    df["BB_Upper"] = sma + (std * 2.0)
    df["BB_Middle"] = sma
    df["BB_Lower"] = sma - (std * 2.0)
    df["BB_Width"] = (df["BB_Upper"] - df["BB_Lower"]) / sma * 100
    df["BB_Width_MA"] = df["BB_Width"].rolling(window=10).mean()

    # RSI (14-day)
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD (12, 26, 9)
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9).mean()
    df["MACD_Histogram"] = df["MACD"] - df["MACD_Signal"]

    # Volume (20-day average)
    df["Volume_MA"] = volume.rolling(window=20).mean()
    df["Volume_Ratio"] = volume / df["Volume_MA"]

    # Squeeze detection (bandwidth < 70% of 10-day average)
    df["In_Squeeze"] = df["BB_Width"] < (df["BB_Width_MA"] * 0.7)

    return df


def calculate_confidence_score(volume_pass: bool, rsi_pass: bool, macd_pass: bool) -> int:
    """
    Calculate signal confidence score (0-100 points).

    Scoring:
        - Base (Bollinger breakout): 25 points
        - Volume filter passed: +25 points
        - RSI neutral zone: +20 points
        - MACD bullish: +30 points

    Args:
        volume_pass: Volume >= 1.5x 20-day average
        rsi_pass: RSI in neutral zone (30-70)
        macd_pass: MACD histogram > 0

    Returns:
        Confidence score (0-100)
    """
    score = 25  # Base score for Bollinger breakout
    if volume_pass:
        score += 25
    if rsi_pass:
        score += 20
    if macd_pass:
        score += 30
    return score


class SignalScanner:
    """Scans stock universe for trading signals."""

    def __init__(
        self,
        confidence_threshold: int = 60,
        stop_loss_percent: float = 5.0,
        take_profit_pct: float = 10.0,
        take_profit_ratio: float = 0.5,
    ):
        if not 1.0 <= stop_loss_percent <= 20.0:
            raise ValueError("stop_loss_percent must be between 1.0 and 20.0")
        if not 5.0 <= take_profit_pct <= 50.0:
            raise ValueError("take_profit_pct must be between 5.0 and 50.0")
        if not 0.1 <= take_profit_ratio <= 1.0:
            raise ValueError("take_profit_ratio must be between 0.1 and 1.0")

        self.confidence_threshold = confidence_threshold
        self.stop_loss_percent = stop_loss_percent
        self.take_profit_pct = take_profit_pct
        self.take_profit_ratio = take_profit_ratio

    def scan_for_buy_signals(
        self,
        stock_codes: List[str],
        existing_positions: List[str],
        progress_callback=None,
    ) -> List[StockSignal]:
        """
        Scan for BUY signals on stocks without positions.

        Args:
            stock_codes: List of stock codes to scan
            existing_positions: List of stock codes already in portfolio
            progress_callback: Optional callback(current, total, stock_code)

        Returns:
            List of StockSignal objects for BUY recommendations
        """
        signals = []

        # Filter out stocks we already own
        candidates = [s for s in stock_codes if s not in existing_positions]
        total = len(candidates)

        for i, stock_code in enumerate(candidates):
            if progress_callback:
                progress_callback(i + 1, total, stock_code)

            df = fetch_stock_data(stock_code)
            if df is None or len(df) < 35:
                continue

            df = calculate_indicators(df)
            latest = df.iloc[-1]

            # Skip if indicators are NaN
            if pd.isna(latest["BB_Upper"]) or pd.isna(latest["RSI"]):
                continue

            # Check BUY conditions
            # 1. Price above upper Bollinger Band (breakout)
            price_breakout = latest["Close"] > latest["BB_Upper"]

            # 2. Bandwidth expanding (was in squeeze recently)
            was_in_squeeze = df["In_Squeeze"].iloc[-5:-1].any()
            bandwidth_expanding = latest["BB_Width"] > df["BB_Width"].iloc[-2]

            # 3. Volume filter (1.5x average)
            volume_pass = latest["Volume_Ratio"] >= 1.5

            # 4. RSI neutral (30-70)
            rsi_pass = 30 <= latest["RSI"] <= 70

            # 5. MACD bullish (histogram > 0)
            macd_pass = latest["MACD_Histogram"] > 0

            if price_breakout and (was_in_squeeze or bandwidth_expanding):
                confidence = calculate_confidence_score(volume_pass, rsi_pass, macd_pass)

                if confidence >= self.confidence_threshold:
                    stock_name = get_stock_name(stock_code)
                    signals.append(
                        StockSignal(
                            stock_code=stock_code,
                            stock_name=stock_name,
                            signal_type="BUY",
                            confidence_score=confidence,
                            current_price=float(latest["Close"]),
                            reason="squeeze_breakout_buy",
                            indicators={
                                "rsi": float(latest["RSI"]),
                                "macd_histogram": float(latest["MACD_Histogram"]),
                                "volume_ratio": float(latest["Volume_Ratio"]),
                                "bb_width": float(latest["BB_Width"]),
                                "bb_upper": float(latest["BB_Upper"]),
                                "bb_middle": float(latest["BB_Middle"]),
                                "bb_lower": float(latest["BB_Lower"]),
                            },
                        )
                    )

        # Sort by confidence score descending
        signals.sort(key=lambda x: x.confidence_score, reverse=True)
        return signals

    def scan_for_sell_signals(
        self, positions: List[WizardPosition], progress_callback=None
    ) -> List[StockSignal]:
        """
        Scan for SELL signals on existing positions using common sell strategy.

        Args:
            positions: List of current positions
            progress_callback: Optional callback(current, total, stock_code)

        Returns:
            List of StockSignal objects for SELL recommendations
        """
        signals = []
        total = len(positions)

        sell_config = SellStrategyConfig(
            stop_loss_pct=self.stop_loss_percent,
            take_profit_pct=self.take_profit_pct,
            take_profit_ratio=self.take_profit_ratio,
        )

        for i, pos in enumerate(positions):
            if progress_callback:
                progress_callback(i + 1, total, pos.stock_code)

            df = fetch_stock_data(pos.stock_code)
            if df is None:
                continue

            df = calculate_indicators(df)
            latest = df.iloc[-1]
            current_price = float(latest["Close"])

            pnl_pct = ((current_price - pos.entry_price) / pos.entry_price) * 100
            bb_middle = float(latest["BB_Middle"]) if not pd.isna(latest["BB_Middle"]) else None

            sell_signal = evaluate_sell_conditions(
                pnl_pct=pnl_pct,
                current_price=current_price,
                bb_middle=bb_middle,
                quantity=pos.quantity,
                partial_take_profit_executed=pos.partial_take_profit_executed,
                config=sell_config,
            )

            if sell_signal.should_sell:
                stock_name = get_stock_name(pos.stock_code)
                confidence = 100 - (sell_signal.priority - 1) * 10
                signals.append(
                    StockSignal(
                        stock_code=pos.stock_code,
                        stock_name=stock_name,
                        signal_type="SELL",
                        confidence_score=confidence,
                        current_price=current_price,
                        reason=sell_signal.reason.value,
                        indicators={
                            "entry_price": pos.entry_price,
                            "pnl_pct": pnl_pct,
                            "rsi": float(latest["RSI"]) if not pd.isna(latest["RSI"]) else 0.0,
                            "bb_lower": float(latest["BB_Lower"])
                            if not pd.isna(latest["BB_Lower"])
                            else 0.0,
                            "bb_middle": bb_middle if bb_middle else 0.0,
                            "sell_quantity": sell_signal.sell_quantity,
                            "sell_ratio": sell_signal.sell_ratio,
                        },
                    )
                )

        return signals

    def get_current_prices(self, stock_codes: List[str]) -> Dict[str, float]:
        """
        Get current prices for a list of stocks.

        Args:
            stock_codes: List of stock codes

        Returns:
            Dict of stock_code -> current_price
        """
        prices = {}
        for stock_code in stock_codes:
            df = fetch_stock_data(stock_code, days=5)
            if df is not None and len(df) > 0:
                prices[stock_code] = float(df.iloc[-1]["Close"])
        return prices
