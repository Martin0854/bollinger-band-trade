#!/usr/bin/env python3
"""Quick Time Period Validation with fewer periods and stocks for faster results."""

import json
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


def calculate_bollinger_bands(close, window=20, num_std=2.0):
    sma = close.rolling(window=window).mean()
    std = close.rolling(window=window).std()
    upper = sma + (std * num_std)
    lower = sma - (std * num_std)
    width = (upper - lower) / sma * 100
    width_ma = width.rolling(window=10).mean()
    return upper, sma, lower, width, width_ma


def calculate_rsi(close, window=14):
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_macd(close, fast_period=12, slow_period=26, signal_period=9):
    ema_fast = close.ewm(span=fast_period).mean()
    ema_slow = close.ewm(span=slow_period).mean()
    macd = ema_fast - ema_slow
    signal = macd.ewm(span=signal_period).mean()
    histogram = macd - signal
    return macd, signal, histogram


def calculate_volume_ratio(volume, window=20):
    return volume / volume.rolling(window=window).mean()


def calculate_all_indicators(df, bb_window=20, bb_std=2.0, squeeze_threshold=0.7):
    df = df.copy()
    close, volume = df["Close"], df["Volume"]
    bb_upper, bb_middle, bb_lower, bb_width, bb_width_ma = calculate_bollinger_bands(
        close, bb_window, bb_std
    )
    df["BB_Upper"], df["BB_Middle"], df["BB_Lower"] = bb_upper, bb_middle, bb_lower
    df["BB_Width"], df["BB_Width_MA"] = bb_width, bb_width_ma
    df["RSI"] = calculate_rsi(close, 14)
    macd_line, macd_sig, macd_hist = calculate_macd(close, 12, 26, 9)
    df["MACD"], df["MACD_Signal"], df["MACD_Histogram"] = macd_line, macd_sig, macd_hist
    df["Volume_Ratio"] = calculate_volume_ratio(volume, 20)
    df["In_Squeeze"] = df["BB_Width"] < (df["BB_Width_MA"] * squeeze_threshold)
    df["MA_200"] = close.rolling(window=200).mean()
    return df


def calculate_confidence_score(volume_ratio, rsi, macd_histogram, macd_signal):
    score = 25.0
    if volume_ratio > 1.0:
        score += min(25.0, (volume_ratio - 1.0) * 25.0)
    if 30 <= rsi <= 70:
        score += 20.0 * (1 - abs(rsi - 50) / 20.0)
    if macd_histogram > 0:
        macd_signal_abs = abs(macd_signal) if macd_signal != 0 else 0.001
        score += 30.0 * min(macd_histogram / macd_signal_abs, 1.0)
    return score


@dataclass
class Position:
    stock_code: str
    stock_name: str
    quantity: int
    entry_price: float
    entry_date: str
    partial_take_profit_executed: bool = False


@dataclass
class Trade:
    date: str
    stock_code: str
    action: str
    price: float
    quantity: int
    reason: str
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None


@dataclass
class BacktestState:
    initial_capital: float
    cash: float
    positions: dict = field(default_factory=dict)
    trades: list = field(default_factory=list)
    daily_values: list = field(default_factory=list)


@dataclass
class BacktestParams:
    max_positions: int = 15
    max_position_pct: float = 10.0
    stop_loss_pct: float = 5.0
    take_profit_pct: float = 10.0
    take_profit_ratio: float = 0.5
    confidence_threshold: int = 60
    bb_window: int = 20
    bb_std: float = 2.0
    squeeze_threshold: float = 0.7
    sell_on_middle_band: bool = True
    require_trend_up: bool = False
    name: str = "unnamed"


class BacktestEngine:
    def __init__(self, params: BacktestParams):
        self.params = params

    def run_backtest(
        self, stock_codes, stock_names, start_date, end_date, initial_capital=10_000_000
    ):
        all_data = self._fetch_all_data(stock_codes, start_date, end_date)
        for code in all_data:
            all_data[code] = calculate_all_indicators(
                all_data[code],
                self.params.bb_window,
                self.params.bb_std,
                self.params.squeeze_threshold,
            )
        state = self._run_simulation(all_data, stock_names, start_date, end_date, initial_capital)
        return self._analyze_performance(state, initial_capital)

    def _fetch_all_data(self, stock_codes, start_date, end_date):
        start_with_buffer = start_date - timedelta(days=250)
        all_data = {}
        for code in stock_codes:
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

    def _run_simulation(self, all_data, stock_names, start_date, end_date, initial_capital):
        state = BacktestState(initial_capital=initial_capital, cash=initial_capital)
        if not all_data:
            return state
        sample_df = list(all_data.values())[0]
        try:
            trading_days = sample_df.loc[str(start_date) : str(end_date)].index.tolist()
        except Exception:
            return state

        for trading_date in trading_days:
            date_str = trading_date.strftime("%Y-%m-%d")

            positions_to_sell = []
            for code, pos in state.positions.items():
                if code not in all_data:
                    continue
                sell_signal = self._check_sell_signal(all_data[code], date_str, pos)
                if sell_signal:
                    positions_to_sell.append((code, sell_signal))

            for code, signal in positions_to_sell:
                pos = state.positions[code]
                sell_ratio = signal.get("sell_ratio", 1.0)
                sell_quantity = int(pos.quantity * sell_ratio) or pos.quantity
                proceeds = signal["price"] * sell_quantity
                pnl = (signal["price"] - pos.entry_price) * sell_quantity
                state.cash += proceeds
                state.trades.append(
                    Trade(
                        date_str,
                        code,
                        "SELL",
                        signal["price"],
                        sell_quantity,
                        signal["reason"],
                        pnl,
                        signal["pnl_pct"],
                    )
                )
                if sell_ratio >= 1.0 or sell_quantity >= pos.quantity:
                    del state.positions[code]
                else:
                    pos.quantity -= sell_quantity
                    if signal["reason"] == "take_profit_target_hit":
                        pos.partial_take_profit_executed = True

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
                    max_allocation = initial_capital * (self.params.max_position_pct / 100)
                    quantity = min(
                        int(max_allocation / signal["price"]), int(state.cash / signal["price"])
                    )
                    if quantity < 1 or signal["price"] * quantity > state.cash:
                        continue
                    state.cash -= signal["price"] * quantity
                    state.positions[code] = Position(
                        code, stock_names.get(code, code), quantity, signal["price"], date_str
                    )
                    state.trades.append(
                        Trade(date_str, code, "BUY", signal["price"], quantity, f"squeeze_breakout")
                    )

            positions_value = (
                sum(
                    float(all_data[c].loc[all_data[c].index <= trading_date].iloc[-1]["Close"])
                    * p.quantity
                    for c, p in state.positions.items()
                    if c in all_data
                )
                if state.positions
                else 0
            )
            state.daily_values.append((date_str, state.cash + positions_value))
        return state

    def _check_buy_signal(self, df, date_str):
        try:
            idx = df.index.get_loc(pd.Timestamp(date_str))
            if idx < 30:
                return None
            row = df.iloc[idx]
            prev_rows = df.iloc[idx - 5 : idx]
            if pd.isna(row["BB_Upper"]) or pd.isna(row["RSI"]):
                return None
            if self.params.require_trend_up and (
                pd.isna(row["MA_200"]) or row["Close"] < row["MA_200"]
            ):
                return None
            price_breakout = row["Close"] > row["BB_Upper"]
            was_in_squeeze = prev_rows["In_Squeeze"].any()
            bandwidth_expanding = row["BB_Width"] > df.iloc[idx - 1]["BB_Width"]
            if price_breakout and (was_in_squeeze or bandwidth_expanding):
                confidence = calculate_confidence_score(
                    float(row["Volume_Ratio"]),
                    float(row["RSI"]),
                    float(row["MACD_Histogram"]),
                    float(row["MACD_Signal"]),
                )
                if confidence >= self.params.confidence_threshold:
                    return {"price": float(row["Close"]), "confidence": confidence}
        except (KeyError, IndexError):
            pass
        return None

    def _check_sell_signal(self, df, date_str, position):
        try:
            idx = df.index.get_loc(pd.Timestamp(date_str))
            row = df.iloc[idx]
            current_price = float(row["Close"])
            pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100
            if pnl_pct <= -self.params.stop_loss_pct:
                return {
                    "price": current_price,
                    "reason": f"stop_loss",
                    "pnl_pct": pnl_pct,
                    "sell_ratio": 1.0,
                }
            if pnl_pct >= self.params.take_profit_pct and not position.partial_take_profit_executed:
                return {
                    "price": current_price,
                    "reason": "take_profit_target_hit",
                    "pnl_pct": pnl_pct,
                    "sell_ratio": self.params.take_profit_ratio,
                }
            if self.params.sell_on_middle_band:
                bb_middle = row["BB_Middle"]
                if not pd.isna(bb_middle) and current_price < bb_middle:
                    return {
                        "price": current_price,
                        "reason": "trend_broken",
                        "pnl_pct": pnl_pct,
                        "sell_ratio": 1.0,
                    }
        except (KeyError, IndexError):
            pass
        return None

    def _analyze_performance(self, state, initial_capital):
        final_value = state.daily_values[-1][1] if state.daily_values else initial_capital
        total_return = ((final_value - initial_capital) / initial_capital) * 100
        sell_trades = [t for t in state.trades if t.action == "SELL"]
        winning_trades = [t for t in sell_trades if t.pnl and t.pnl > 0]
        win_rate = (len(winning_trades) / len(sell_trades) * 100) if sell_trades else 0
        values = [v[1] for v in state.daily_values]
        max_drawdown = 0
        if values:
            peak = values[0]
            for v in values:
                if v > peak:
                    peak = v
                max_drawdown = max(max_drawdown, (peak - v) / peak * 100)
        sharpe_ratio = 0
        if len(state.daily_values) > 1:
            returns = [
                (state.daily_values[i][1] - state.daily_values[i - 1][1])
                / state.daily_values[i - 1][1]
                for i in range(1, len(state.daily_values))
            ]
            if returns:
                avg_return, std_return = np.mean(returns), np.std(returns)
                if std_return > 0:
                    sharpe_ratio = (avg_return / std_return) * np.sqrt(252)
        return {
            "total_return_pct": total_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "total_trades": len(state.trades),
        }


STRATEGIES = {
    "baseline": BacktestParams(name="baseline"),
    "original_optimal": BacktestParams(
        name="original_optimal",
        bb_window=12,
        bb_std=1.3,
        squeeze_threshold=0.55,
        confidence_threshold=50,
        stop_loss_pct=4.5,
        take_profit_pct=9.0,
        sell_on_middle_band=False,
    ),
    "robust_standard": BacktestParams(
        name="robust_standard",
        bb_window=20,
        bb_std=2.0,
        squeeze_threshold=0.7,
        confidence_threshold=55,
        stop_loss_pct=5.0,
        take_profit_pct=10.0,
        sell_on_middle_band=False,
        require_trend_up=True,
    ),
}

PERIODS = [
    {"start": date(2023, 1, 1), "end": date(2023, 6, 30), "name": "2023H1", "type": "6M"},
    {"start": date(2023, 7, 1), "end": date(2023, 12, 31), "name": "2023H2", "type": "6M"},
    {"start": date(2024, 1, 1), "end": date(2024, 6, 30), "name": "2024H1", "type": "6M"},
    {"start": date(2024, 7, 1), "end": date(2024, 12, 31), "name": "2024H2", "type": "6M"},
    {"start": date(2025, 1, 1), "end": date(2025, 6, 30), "name": "2025H1", "type": "6M"},
    {"start": date(2023, 1, 1), "end": date(2023, 12, 31), "name": "2023", "type": "1Y"},
    {"start": date(2024, 1, 1), "end": date(2024, 12, 31), "name": "2024", "type": "1Y"},
    {"start": date(2025, 1, 1), "end": date(2025, 12, 31), "name": "2025", "type": "1Y"},
    {"start": date(2023, 1, 1), "end": date(2025, 12, 31), "name": "2023-2025", "type": "3Y"},
]


def load_stock_list(filepath):
    with open(filepath) as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def load_stock_names(filepath="data/stock_names_kr.json"):
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def run_single_backtest(args):
    strategy_name, params, stock_codes, stock_names, period = args
    engine = BacktestEngine(params)
    result = engine.run_backtest(
        stock_codes, stock_names, period["start"], period["end"], 10_000_000
    )
    return {
        "strategy": strategy_name,
        "period": period["name"],
        "period_type": period["type"],
        "metrics": result,
    }


def main():
    print("=" * 70)
    print("QUICK TIME PERIOD VALIDATION")
    print("=" * 70)

    stock_codes = load_stock_list("kospi_top100.txt")[:50]
    stock_names = load_stock_names()

    print(f"\nLoaded {len(stock_codes)} stocks (limited for speed)")
    print(
        f"Testing {len(STRATEGIES)} strategies x {len(PERIODS)} periods = {len(STRATEGIES) * len(PERIODS)} backtests\n"
    )

    experiment_args = [
        (sn, sp, stock_codes, stock_names, p) for sn, sp in STRATEGIES.items() for p in PERIODS
    ]

    results = []
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(run_single_backtest, args): args for args in experiment_args}
        for i, future in enumerate(as_completed(futures)):
            try:
                result = future.result()
                results.append(result)
                m = result["metrics"]
                print(
                    f"[{i + 1}/{len(experiment_args)}] {result['strategy']} ({result['period']}): "
                    f"{m['total_return_pct']:.2f}% return, {m['sharpe_ratio']:.2f} Sharpe"
                )
            except Exception as e:
                print(f"[{i + 1}/{len(experiment_args)}] FAILED: {e}")

    Path("reports").mkdir(exist_ok=True)

    by_strategy = {}
    for r in results:
        strat = r["strategy"]
        if strat not in by_strategy:
            by_strategy[strat] = {}
        by_strategy[strat][r["period"]] = r["metrics"]

    report = ["# Quick Time Period Validation Report\n", f"Generated: {date.today().isoformat()}\n"]

    for period_type in ["6M", "1Y", "3Y"]:
        type_periods = [p for p in PERIODS if p["type"] == period_type]
        if not type_periods:
            continue
        report.append(f"\n## {period_type} Periods\n")
        report.append("| Strategy | Period | Return | Sharpe | MDD | Win Rate | Trades |")
        report.append("|----------|--------|--------|--------|-----|----------|--------|")
        for strat_name, strat_results in by_strategy.items():
            for p in type_periods:
                if p["name"] in strat_results:
                    m = strat_results[p["name"]]
                    report.append(
                        f"| {strat_name} | {p['name']} | {m['total_return_pct']:.2f}% | "
                        f"{m['sharpe_ratio']:.2f} | {m['max_drawdown']:.2f}% | {m['win_rate']:.1f}% | {m['total_trades']} |"
                    )

    report.append("\n## Strategy Consistency Analysis\n")
    for strat_name, strat_results in by_strategy.items():
        six_m = [v["total_return_pct"] for k, v in strat_results.items() if "H" in k]
        one_y = [v["total_return_pct"] for k, v in strat_results.items() if k.isdigit()]
        if six_m:
            pos_6m = sum(1 for r in six_m if r > 0)
            report.append(
                f"**{strat_name}**: 6M avg={np.mean(six_m):.2f}%, positive={pos_6m}/{len(six_m)}"
            )
        if one_y:
            pos_1y = sum(1 for r in one_y if r > 0)
            report.append(f"  1Y avg={np.mean(one_y):.2f}%, positive={pos_1y}/{len(one_y)}")

    with open("reports/quick_time_validation.md", "w") as f:
        f.write("\n".join(report))
    with open("reports/quick_time_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("\n" + "=" * 70)
    print("Results saved to reports/quick_time_validation.md")


if __name__ == "__main__":
    main()
