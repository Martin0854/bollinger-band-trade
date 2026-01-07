#!/usr/bin/env python3
"""
Validation Runner: Tests if 2023-2025 optimal parameters are valid for 2020-2023.
Runs multiple experiments in parallel and generates comprehensive reports.
"""

import json
import os
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# ================= Configuration =================

# Period definitions
PERIOD_2023_2025 = {"start": date(2023, 1, 1), "end": date(2025, 12, 31), "name": "2023-2025"}
PERIOD_2020_2023 = {"start": date(2020, 1, 1), "end": date(2023, 12, 31), "name": "2020-2023"}

# ================= Indicator Calculations =================


def calculate_bollinger_bands(
    close: pd.Series, window: int = 20, num_std: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger Bands."""
    sma = close.rolling(window=window).mean()
    std = close.rolling(window=window).std()
    upper = sma + (std * num_std)
    lower = sma - (std * num_std)
    width = (upper - lower) / sma * 100
    width_ma = width.rolling(window=10).mean()
    return upper, sma, lower, width, width_ma


def calculate_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """Calculate RSI."""
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_macd(
    close: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD."""
    ema_fast = close.ewm(span=fast_period).mean()
    ema_slow = close.ewm(span=slow_period).mean()
    macd = ema_fast - ema_slow
    signal = macd.ewm(span=signal_period).mean()
    histogram = macd - signal
    return macd, signal, histogram


def calculate_volume_ratio(volume: pd.Series, window: int = 20) -> pd.Series:
    """Calculate volume ratio."""
    volume_ma = volume.rolling(window=window).mean()
    return volume / volume_ma


def calculate_atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """Calculate Average True Range."""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=window).mean()


def calculate_all_indicators(
    df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    rsi_window: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    volume_window: int = 20,
    squeeze_threshold: float = 0.7,
    atr_window: int = 14,
) -> pd.DataFrame:
    """Calculate all technical indicators with configurable parameters."""
    df = df.copy()
    close = df["Close"]
    volume = df["Volume"]

    # Bollinger Bands
    bb_upper, bb_middle, bb_lower, bb_width, bb_width_ma = calculate_bollinger_bands(
        close, window=bb_window, num_std=bb_std
    )
    df["BB_Upper"] = bb_upper
    df["BB_Middle"] = bb_middle
    df["BB_Lower"] = bb_lower
    df["BB_Width"] = bb_width
    df["BB_Width_MA"] = bb_width_ma

    # RSI
    df["RSI"] = calculate_rsi(close, window=rsi_window)

    # MACD
    macd_line, macd_sig, macd_hist = calculate_macd(
        close, fast_period=macd_fast, slow_period=macd_slow, signal_period=macd_signal
    )
    df["MACD"] = macd_line
    df["MACD_Signal"] = macd_sig
    df["MACD_Histogram"] = macd_hist

    # Volume
    df["Volume_MA"] = volume.rolling(window=volume_window).mean()
    df["Volume_Ratio"] = calculate_volume_ratio(volume, window=volume_window)

    # Squeeze detection
    df["In_Squeeze"] = df["BB_Width"] < (df["BB_Width_MA"] * squeeze_threshold)

    # ATR
    df["ATR"] = calculate_atr(df, window=atr_window)

    # 200-day MA for trend filter
    df["MA_200"] = close.rolling(window=200).mean()

    return df


def calculate_confidence_score(
    volume_ratio: float,
    rsi: float,
    macd_histogram: float,
    macd_signal: float,
    volume_weight: float = 25.0,
    rsi_weight: float = 20.0,
    macd_weight: float = 30.0,
) -> float:
    """Calculate signal confidence score with configurable weights."""
    score = 25.0  # Base score for Bollinger breakout

    # Volume Score
    if volume_ratio > 1.0:
        vol_score = min(volume_weight, (volume_ratio - 1.0) * volume_weight)
        score += vol_score

    # RSI Score
    if 30 <= rsi <= 70:
        distance = abs(rsi - 50)
        rsi_score = rsi_weight * (1 - distance / 20.0)
        score += rsi_score

    # MACD Score
    if macd_histogram > 0:
        macd_signal_abs = abs(macd_signal) if macd_signal != 0 else 0.001
        macd_ratio = min(macd_histogram / macd_signal_abs, 1.0)
        macd_score = macd_weight * macd_ratio
        score += macd_score

    return score


# ================= Backtest Data Classes =================


@dataclass
class Position:
    """Backtest position."""

    stock_code: str
    stock_name: str
    quantity: int
    entry_price: float
    entry_date: str
    partial_take_profit_executed: bool = False
    highest_price: float = 0.0  # For trailing stop


@dataclass
class Trade:
    """Backtest trade record."""

    date: str
    stock_code: str
    stock_name: str
    action: str
    price: float
    quantity: int
    reason: str
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None


@dataclass
class BacktestState:
    """Backtest simulation state."""

    initial_capital: float
    cash: float
    positions: dict[str, Position] = field(default_factory=dict)
    trades: list[Trade] = field(default_factory=list)
    daily_values: list[tuple[str, float]] = field(default_factory=list)


@dataclass
class BacktestParams:
    """All backtest parameters."""

    # Position management
    max_positions: int = 15
    max_position_pct: float = 10.0

    # Stop loss and take profit
    stop_loss_pct: float = 5.0
    take_profit_pct: float = 10.0
    take_profit_ratio: float = 0.5

    # Signal generation
    confidence_threshold: int = 60

    # Bollinger Bands
    bb_window: int = 20
    bb_std: float = 2.0

    # RSI
    rsi_window: int = 14

    # MACD
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9

    # Volume
    volume_window: int = 20

    # Squeeze
    squeeze_threshold: float = 0.7

    # Confidence scoring weights
    volume_weight: float = 25.0
    rsi_weight: float = 20.0
    macd_weight: float = 30.0

    # Sell strategies
    sell_on_middle_band: bool = True
    use_trailing_stop: bool = False
    trailing_stop_pct: float = 5.0
    use_atr_stop: bool = False
    atr_multiplier: float = 2.0

    # Entry filters
    require_trend_up: bool = False  # Price > 200 MA

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "max_positions": self.max_positions,
            "max_position_pct": self.max_position_pct,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "take_profit_ratio": self.take_profit_ratio,
            "confidence_threshold": self.confidence_threshold,
            "bb_window": self.bb_window,
            "bb_std": self.bb_std,
            "rsi_window": self.rsi_window,
            "macd_fast": self.macd_fast,
            "macd_slow": self.macd_slow,
            "macd_signal": self.macd_signal,
            "volume_window": self.volume_window,
            "squeeze_threshold": self.squeeze_threshold,
            "volume_weight": self.volume_weight,
            "rsi_weight": self.rsi_weight,
            "macd_weight": self.macd_weight,
            "sell_on_middle_band": self.sell_on_middle_band,
            "use_trailing_stop": self.use_trailing_stop,
            "trailing_stop_pct": self.trailing_stop_pct,
            "use_atr_stop": self.use_atr_stop,
            "atr_multiplier": self.atr_multiplier,
            "require_trend_up": self.require_trend_up,
        }


# ================= Backtest Engine =================


class BacktestEngine:
    """Standalone backtest engine with extended features."""

    def __init__(self, params: BacktestParams):
        self.params = params

    def run_backtest(
        self,
        stock_codes: list[str],
        stock_names: dict[str, str],
        start_date: date,
        end_date: date,
        initial_capital: float = 10_000_000,
        verbose: bool = False,
    ) -> dict:
        """Run backtest simulation."""
        # Fetch data
        all_data = self._fetch_all_data(stock_codes, start_date, end_date, verbose)

        if verbose:
            print(f"Fetched data for {len(all_data)} stocks")

        # Calculate indicators
        for code in all_data:
            all_data[code] = calculate_all_indicators(
                all_data[code],
                bb_window=self.params.bb_window,
                bb_std=self.params.bb_std,
                rsi_window=self.params.rsi_window,
                macd_fast=self.params.macd_fast,
                macd_slow=self.params.macd_slow,
                macd_signal=self.params.macd_signal,
                volume_window=self.params.volume_window,
                squeeze_threshold=self.params.squeeze_threshold,
            )

        # Run simulation
        state = self._run_simulation(
            all_data=all_data,
            stock_names=stock_names,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
        )

        # Analyze results
        metrics = self._analyze_performance(state, initial_capital)

        return {
            "params": self.params.to_dict(),
            "metrics": metrics,
            "trades": [
                {
                    "date": t.date,
                    "stock_code": t.stock_code,
                    "action": t.action,
                    "price": t.price,
                    "quantity": t.quantity,
                    "reason": t.reason,
                    "pnl": t.pnl,
                    "pnl_pct": t.pnl_pct,
                }
                for t in state.trades
            ],
            "daily_values": [{"date": d, "value": v} for d, v in state.daily_values],
        }

    def _fetch_all_data(
        self,
        stock_codes: list[str],
        start_date: date,
        end_date: date,
        verbose: bool = False,
    ) -> dict[str, pd.DataFrame]:
        """Fetch all stock data upfront."""
        start_with_buffer = start_date - timedelta(days=250)  # For 200 MA
        all_data = {}

        for i, code in enumerate(stock_codes):
            if verbose and (i + 1) % 20 == 0:
                print(f"  Fetching data... {i + 1}/{len(stock_codes)}")

            ticker = f"{code}.KS"
            try:
                df = yf.download(
                    ticker,
                    start=start_with_buffer.isoformat(),
                    end=(end_date + timedelta(days=1)).isoformat(),
                    progress=False,
                    auto_adjust=False,
                )

                if df.empty:
                    ticker = f"{code}.KQ"
                    df = yf.download(
                        ticker,
                        start=start_with_buffer.isoformat(),
                        end=(end_date + timedelta(days=1)).isoformat(),
                        progress=False,
                        auto_adjust=False,
                    )

                if not df.empty and len(df) >= 30:
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    all_data[code] = df[["Open", "High", "Low", "Close", "Volume"]].dropna()

            except Exception:
                pass

        return all_data

    def _run_simulation(
        self,
        all_data: dict[str, pd.DataFrame],
        stock_names: dict[str, str],
        start_date: date,
        end_date: date,
        initial_capital: float,
    ) -> BacktestState:
        """Run the backtest simulation."""
        state = BacktestState(initial_capital=initial_capital, cash=initial_capital)

        if not all_data:
            return state

        sample_df = list(all_data.values())[0]
        trading_days = sample_df.loc[str(start_date) : str(end_date)].index.tolist()

        for trading_date in trading_days:
            date_str = trading_date.strftime("%Y-%m-%d")

            for code, pos in state.positions.items():
                if code in all_data:
                    try:
                        idx = all_data[code].index.get_loc(trading_date)
                        current_high = float(all_data[code].iloc[idx]["High"])
                        if current_high > pos.highest_price:
                            pos.highest_price = current_high
                    except (KeyError, IndexError):
                        pass

            # 1. Check SELL signals
            positions_to_sell = []
            for code, pos in state.positions.items():
                if code not in all_data:
                    continue

                sell_signal = self._check_sell_signal(all_data[code], date_str, pos)
                if sell_signal:
                    positions_to_sell.append((code, sell_signal))

            # Execute sells
            for code, signal in positions_to_sell:
                pos = state.positions[code]
                sell_ratio = signal.get("sell_ratio", 1.0)
                sell_quantity = int(pos.quantity * sell_ratio)
                if sell_quantity < 1:
                    sell_quantity = pos.quantity

                proceeds = signal["price"] * sell_quantity
                pnl = (signal["price"] - pos.entry_price) * sell_quantity
                pnl_pct = signal["pnl_pct"]

                state.cash += proceeds
                state.trades.append(
                    Trade(
                        date=date_str,
                        stock_code=code,
                        stock_name=pos.stock_name,
                        action="SELL",
                        price=signal["price"],
                        quantity=sell_quantity,
                        reason=signal["reason"],
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                    )
                )

                if sell_ratio >= 1.0 or sell_quantity >= pos.quantity:
                    del state.positions[code]
                else:
                    pos.quantity -= sell_quantity
                    if signal["reason"] == "take_profit_target_hit":
                        pos.partial_take_profit_executed = True

            # 2. Check BUY signals
            if len(state.positions) < self.params.max_positions:
                buy_candidates = []

                for code, df in all_data.items():
                    if code in state.positions:
                        continue

                    buy_signal = self._check_buy_signal(df, date_str)
                    if buy_signal:
                        buy_candidates.append((code, buy_signal))

                buy_candidates.sort(key=lambda x: x[1]["confidence"], reverse=True)

                for code, signal in buy_candidates:
                    if len(state.positions) >= self.params.max_positions:
                        break

                    quantity = self._calculate_position_size(
                        signal["price"], state.cash, initial_capital
                    )
                    if quantity < 1:
                        continue

                    cost = signal["price"] * quantity
                    if cost > state.cash:
                        continue

                    state.cash -= cost
                    state.positions[code] = Position(
                        stock_code=code,
                        stock_name=stock_names.get(code, code),
                        quantity=quantity,
                        entry_price=signal["price"],
                        entry_date=date_str,
                        highest_price=signal["price"],
                    )
                    state.trades.append(
                        Trade(
                            date=date_str,
                            stock_code=code,
                            stock_name=stock_names.get(code, code),
                            action="BUY",
                            price=signal["price"],
                            quantity=quantity,
                            reason=f"squeeze_breakout (conf:{signal['confidence']:.0f})",
                        )
                    )

            # 3. Calculate daily value
            positions_value = 0
            for code, pos in state.positions.items():
                if code in all_data:
                    try:
                        idx = all_data[code].index.get_loc(trading_date)
                        current_price = float(all_data[code].iloc[idx]["Close"])
                        positions_value += current_price * pos.quantity
                    except (KeyError, IndexError):
                        positions_value += pos.entry_price * pos.quantity

            total_value = state.cash + positions_value
            state.daily_values.append((date_str, total_value))

        return state

    def _check_buy_signal(self, df: pd.DataFrame, date_str: str) -> Optional[dict]:
        """Check for buy signal on given date."""
        try:
            idx = df.index.get_loc(pd.Timestamp(date_str))
            if idx < 30:
                return None

            row = df.iloc[idx]
            prev_rows = df.iloc[idx - 5 : idx]

            if pd.isna(row["BB_Upper"]) or pd.isna(row["RSI"]):
                return None

            # Trend filter: only buy if price > 200 MA
            if self.params.require_trend_up:
                if pd.isna(row["MA_200"]) or row["Close"] < row["MA_200"]:
                    return None

            price_breakout = row["Close"] > row["BB_Upper"]
            was_in_squeeze = prev_rows["In_Squeeze"].any()
            bandwidth_expanding = row["BB_Width"] > df.iloc[idx - 1]["BB_Width"]

            if price_breakout and (was_in_squeeze or bandwidth_expanding):
                confidence = calculate_confidence_score(
                    volume_ratio=float(row["Volume_Ratio"]),
                    rsi=float(row["RSI"]),
                    macd_histogram=float(row["MACD_Histogram"]),
                    macd_signal=float(row["MACD_Signal"]),
                    volume_weight=self.params.volume_weight,
                    rsi_weight=self.params.rsi_weight,
                    macd_weight=self.params.macd_weight,
                )

                if confidence >= self.params.confidence_threshold:
                    return {
                        "price": float(row["Close"]),
                        "confidence": confidence,
                    }
        except (KeyError, IndexError):
            pass
        return None

    def _check_sell_signal(
        self,
        df: pd.DataFrame,
        date_str: str,
        position: Position,
    ) -> Optional[dict]:
        """Check for sell signal with multiple strategies."""
        try:
            idx = df.index.get_loc(pd.Timestamp(date_str))
            row = df.iloc[idx]

            current_price = float(row["Close"])
            entry_price = position.entry_price
            pnl_pct = ((current_price - entry_price) / entry_price) * 100

            # 1. ATR-based Stop Loss
            if self.params.use_atr_stop and not pd.isna(row["ATR"]):
                atr_stop = entry_price - (row["ATR"] * self.params.atr_multiplier)
                if current_price < atr_stop:
                    return {
                        "price": current_price,
                        "reason": f"atr_stop ({pnl_pct:.1f}%)",
                        "pnl_pct": pnl_pct,
                        "sell_ratio": 1.0,
                    }

            # 2. Trailing Stop
            if self.params.use_trailing_stop and position.highest_price > 0:
                trailing_stop_price = position.highest_price * (
                    1 - self.params.trailing_stop_pct / 100
                )
                if current_price < trailing_stop_price:
                    return {
                        "price": current_price,
                        "reason": f"trailing_stop ({pnl_pct:.1f}%)",
                        "pnl_pct": pnl_pct,
                        "sell_ratio": 1.0,
                    }

            # 3. Fixed Stop Loss
            if pnl_pct <= -self.params.stop_loss_pct:
                return {
                    "price": current_price,
                    "reason": f"stop_loss ({pnl_pct:.1f}%)",
                    "pnl_pct": pnl_pct,
                    "sell_ratio": 1.0,
                }

            # 4. Take Profit (partial)
            if pnl_pct >= self.params.take_profit_pct and not position.partial_take_profit_executed:
                return {
                    "price": current_price,
                    "reason": "take_profit_target_hit",
                    "pnl_pct": pnl_pct,
                    "sell_ratio": self.params.take_profit_ratio,
                }

            # 5. Trend Breakdown (below middle band)
            if self.params.sell_on_middle_band:
                bb_middle = row["BB_Middle"]
                if not pd.isna(bb_middle) and current_price < bb_middle:
                    return {
                        "price": current_price,
                        "reason": "trend_broken_middle_band",
                        "pnl_pct": pnl_pct,
                        "sell_ratio": 1.0,
                    }

        except (KeyError, IndexError):
            pass
        return None

    def _calculate_position_size(self, price: float, cash: float, initial_capital: float) -> int:
        """Calculate position size."""
        max_allocation = initial_capital * (self.params.max_position_pct / 100)
        max_shares = int(max_allocation / price)
        affordable_shares = int(cash / price)
        return min(max_shares, affordable_shares)

    def _analyze_performance(self, state: BacktestState, initial_capital: float) -> dict:
        """Analyze backtest performance."""
        final_value = state.daily_values[-1][1] if state.daily_values else initial_capital
        total_return = ((final_value - initial_capital) / initial_capital) * 100

        sell_trades = [t for t in state.trades if t.action == "SELL"]
        winning_trades = [t for t in sell_trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in sell_trades if t.pnl and t.pnl <= 0]

        win_rate = (len(winning_trades) / len(sell_trades) * 100) if sell_trades else 0

        total_pnl = sum(t.pnl for t in sell_trades if t.pnl)
        avg_win = float(np.mean([t.pnl for t in winning_trades])) if winning_trades else 0
        avg_loss = float(np.mean([t.pnl for t in losing_trades])) if losing_trades else 0

        # Max drawdown
        values = [v[1] for v in state.daily_values]
        max_drawdown = 0
        if values:
            peak = values[0]
            for v in values:
                if v > peak:
                    peak = v
                drawdown = (peak - v) / peak * 100
                max_drawdown = max(max_drawdown, drawdown)

        # Calculate Sharpe Ratio (annualized)
        sharpe_ratio = 0
        if len(state.daily_values) > 1:
            returns = []
            for i in range(1, len(state.daily_values)):
                prev_val = state.daily_values[i - 1][1]
                curr_val = state.daily_values[i][1]
                daily_return = (curr_val - prev_val) / prev_val
                returns.append(daily_return)

            if returns:
                avg_return = np.mean(returns)
                std_return = np.std(returns)
                if std_return > 0:
                    sharpe_ratio = (avg_return / std_return) * np.sqrt(252)

        return {
            "initial_capital": initial_capital,
            "final_value": final_value,
            "total_return_pct": total_return,
            "total_trades": len(state.trades),
            "buy_trades": len([t for t in state.trades if t.action == "BUY"]),
            "sell_trades": len(sell_trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
        }


# ================= Experiment Definitions =================

EXPERIMENTS = {
    # Baseline parameters
    "baseline": BacktestParams(),
    # Optimal 2023-2025 parameters (from exp9)
    "optimal_2023_2025": BacktestParams(
        bb_window=12,
        bb_std=1.3,
        squeeze_threshold=0.55,
        confidence_threshold=50,
        stop_loss_pct=4.5,
        take_profit_pct=9.0,
        sell_on_middle_band=False,
    ),
    # Variations to test robustness
    "optimal_with_trend_filter": BacktestParams(
        bb_window=12,
        bb_std=1.3,
        squeeze_threshold=0.55,
        confidence_threshold=50,
        stop_loss_pct=4.5,
        take_profit_pct=9.0,
        sell_on_middle_band=False,
        require_trend_up=True,
    ),
    "optimal_with_trailing_stop": BacktestParams(
        bb_window=12,
        bb_std=1.3,
        squeeze_threshold=0.55,
        confidence_threshold=50,
        take_profit_pct=9.0,
        sell_on_middle_band=False,
        use_trailing_stop=True,
        trailing_stop_pct=7.0,
    ),
    "optimal_with_atr_stop": BacktestParams(
        bb_window=12,
        bb_std=1.3,
        squeeze_threshold=0.55,
        confidence_threshold=50,
        take_profit_pct=9.0,
        sell_on_middle_band=False,
        use_atr_stop=True,
        atr_multiplier=2.0,
    ),
    # Conservative version
    "conservative_optimal": BacktestParams(
        bb_window=12,
        bb_std=1.3,
        squeeze_threshold=0.55,
        confidence_threshold=60,  # Higher threshold
        stop_loss_pct=4.0,  # Tighter stop
        take_profit_pct=8.0,
        sell_on_middle_band=False,
        require_trend_up=True,
    ),
    # Aggressive version
    "aggressive_optimal": BacktestParams(
        bb_window=10,
        bb_std=1.2,
        squeeze_threshold=0.5,
        confidence_threshold=45,
        stop_loss_pct=5.0,
        take_profit_pct=12.0,
        sell_on_middle_band=False,
    ),
    # Different BB settings
    "bb_tuning_1": BacktestParams(
        bb_window=15,
        bb_std=1.5,
        squeeze_threshold=0.6,
        confidence_threshold=50,
        stop_loss_pct=4.5,
        take_profit_pct=9.0,
        sell_on_middle_band=False,
    ),
    "bb_tuning_2": BacktestParams(
        bb_window=14,
        bb_std=1.4,
        squeeze_threshold=0.55,
        confidence_threshold=50,
        stop_loss_pct=4.5,
        take_profit_pct=9.0,
        sell_on_middle_band=False,
    ),
}


# ================= Utility Functions =================


def load_stock_list(filepath: str) -> list[str]:
    """Load stock codes from a file."""
    with open(filepath, "r") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def load_stock_names(filepath: str = "data/stock_names_kr.json") -> dict[str, str]:
    """Load stock names from JSON file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def run_single_experiment(args):
    """Run a single experiment (for parallel execution)."""
    exp_name, params, stock_codes, stock_names, period = args

    engine = BacktestEngine(params)
    result = engine.run_backtest(
        stock_codes=stock_codes,
        stock_names=stock_names,
        start_date=period["start"],
        end_date=period["end"],
        initial_capital=10_000_000,
        verbose=False,
    )

    return {
        "experiment": exp_name,
        "period": period["name"],
        "result": result,
    }


def generate_report(results: list[dict], output_dir: str = "reports"):
    """Generate comprehensive validation report."""
    Path(output_dir).mkdir(exist_ok=True)

    # Group by experiment
    by_experiment = {}
    for r in results:
        exp = r["experiment"]
        if exp not in by_experiment:
            by_experiment[exp] = {}
        by_experiment[exp][r["period"]] = r["result"]["metrics"]

    # Generate markdown report
    report = []
    report.append("# Parameter Validation Report")
    report.append(f"\nGenerated: {date.today().isoformat()}\n")
    report.append("## Summary Table\n")
    report.append("| Experiment | Period | Return | Sharpe | MDD | Win Rate | Trades |")
    report.append("|------------|--------|--------|--------|-----|----------|--------|")

    for exp_name, periods in by_experiment.items():
        for period_name, metrics in periods.items():
            report.append(
                f"| {exp_name} | {period_name} | "
                f"{metrics['total_return_pct']:.2f}% | "
                f"{metrics['sharpe_ratio']:.2f} | "
                f"{metrics['max_drawdown']:.2f}% | "
                f"{metrics['win_rate']:.1f}% | "
                f"{metrics['total_trades']} |"
            )

    # Validation analysis
    report.append("\n## Validation Analysis\n")
    report.append("### Is 2023-2025 Optimal Valid for 2020-2023?\n")

    if "optimal_2023_2025" in by_experiment:
        opt = by_experiment["optimal_2023_2025"]
        base = by_experiment.get("baseline", {})

        if "2023-2025" in opt and "2020-2023" in opt:
            report.append(f"- **2023-2025 Return**: {opt['2023-2025']['total_return_pct']:.2f}%")
            report.append(f"- **2020-2023 Return**: {opt['2020-2023']['total_return_pct']:.2f}%")

            diff = opt["2020-2023"]["total_return_pct"] - opt["2023-2025"]["total_return_pct"]
            if diff >= 0:
                report.append(f"- **Verdict**: VALID - Parameters work equally well (+{diff:.2f}%)")
            else:
                report.append(
                    f"- **Verdict**: DEGRADED - Parameters work worse in earlier period ({diff:.2f}%)"
                )

        if "2020-2023" in opt and "2020-2023" in base:
            base_ret = base["2020-2023"]["total_return_pct"]
            opt_ret = opt["2020-2023"]["total_return_pct"]
            report.append(f"\n**vs Baseline (2020-2023)**:")
            report.append(f"- Baseline: {base_ret:.2f}%")
            report.append(f"- Optimal: {opt_ret:.2f}%")
            report.append(f"- Improvement: {opt_ret - base_ret:.2f}%")

    # Per-experiment details
    report.append("\n## Experiment Details\n")
    for exp_name, periods in by_experiment.items():
        report.append(f"### {exp_name}\n")
        for period_name, metrics in periods.items():
            report.append(f"**{period_name}**:")
            report.append(f"- Return: {metrics['total_return_pct']:.2f}%")
            report.append(f"- Sharpe: {metrics['sharpe_ratio']:.2f}")
            report.append(f"- MDD: {metrics['max_drawdown']:.2f}%")
            report.append(f"- Win Rate: {metrics['win_rate']:.1f}%")
            report.append(f"- Trades: {metrics['total_trades']}")
            report.append("")

    # Write report
    report_path = Path(output_dir) / "validation_report.md"
    with open(report_path, "w") as f:
        f.write("\n".join(report))

    print(f"Report saved to: {report_path}")

    # Also save raw JSON
    json_path = Path(output_dir) / "validation_results.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"Raw results saved to: {json_path}")


def main():
    """Main entry point."""
    print("=" * 60)
    print("PARAMETER VALIDATION: 2023-2025 Optimal vs 2020-2023")
    print("=" * 60)

    # Load stock list
    stock_codes = load_stock_list("kospi_top100.txt")[:100]
    stock_names = load_stock_names()

    print(f"\nLoaded {len(stock_codes)} stocks")
    print(
        f"Running {len(EXPERIMENTS)} experiments x 2 periods = {len(EXPERIMENTS) * 2} backtests\n"
    )

    # Prepare experiment arguments
    experiment_args = []
    for exp_name, params in EXPERIMENTS.items():
        for period in [PERIOD_2023_2025, PERIOD_2020_2023]:
            experiment_args.append((exp_name, params, stock_codes, stock_names, period))

    # Run experiments in parallel
    results = []
    max_workers = min(4, len(experiment_args))  # Limit parallel workers

    print(f"Running experiments with {max_workers} parallel workers...")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_single_experiment, args): args for args in experiment_args}

        for i, future in enumerate(as_completed(futures)):
            args = futures[future]
            try:
                result = future.result()
                results.append(result)
                metrics = result["result"]["metrics"]
                print(
                    f"[{i + 1}/{len(experiment_args)}] {result['experiment']} ({result['period']}): "
                    f"{metrics['total_return_pct']:.2f}% return, {metrics['sharpe_ratio']:.2f} Sharpe"
                )
            except Exception as e:
                print(f"[{i + 1}/{len(experiment_args)}] {args[0]} ({args[4]['name']}) FAILED: {e}")

    # Generate report
    print("\nGenerating validation report...")
    generate_report(results)

    print("\nDone!")


if __name__ == "__main__":
    main()
