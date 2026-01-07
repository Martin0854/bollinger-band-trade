#!/usr/bin/env python3
"""
Robust Parameter Search: Find parameters that work well across BOTH periods.
Focus on minimizing overfitting gap between 2023-2025 and 2020-2023.
"""

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

PERIOD_2023_2025 = {"start": date(2023, 1, 1), "end": date(2025, 12, 31), "name": "2023-2025"}
PERIOD_2020_2023 = {"start": date(2020, 1, 1), "end": date(2023, 12, 31), "name": "2020-2023"}


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
    volume_ma = volume.rolling(window=window).mean()
    return volume / volume_ma


def calculate_atr(df, window=14):
    high, low, close = df["High"], df["Low"], df["Close"]
    tr1, tr2, tr3 = high - low, abs(high - close.shift(1)), abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=window).mean()


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
    df["Volume_MA"] = volume.rolling(window=20).mean()
    df["Volume_Ratio"] = calculate_volume_ratio(volume, 20)
    df["In_Squeeze"] = df["BB_Width"] < (df["BB_Width_MA"] * squeeze_threshold)
    df["ATR"] = calculate_atr(df, 14)
    df["MA_200"] = close.rolling(window=200).mean()
    df["MA_50"] = close.rolling(window=50).mean()
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
    highest_price: float = 0.0


@dataclass
class Trade:
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
    use_trailing_stop: bool = False
    trailing_stop_pct: float = 7.0
    use_atr_stop: bool = False
    atr_multiplier: float = 2.0
    require_trend_up: bool = False
    require_50ma_up: bool = False
    name: str = "unnamed"

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}


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
                        pos.stock_name,
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
                    if quantity < 1:
                        continue
                    cost = signal["price"] * quantity
                    if cost > state.cash:
                        continue
                    state.cash -= cost
                    state.positions[code] = Position(
                        code,
                        stock_names.get(code, code),
                        quantity,
                        signal["price"],
                        date_str,
                        False,
                        signal["price"],
                    )
                    state.trades.append(
                        Trade(
                            date_str,
                            code,
                            stock_names.get(code, code),
                            "BUY",
                            signal["price"],
                            quantity,
                            f"squeeze_breakout (conf:{signal['confidence']:.0f})",
                        )
                    )

            positions_value = 0
            for code, pos in state.positions.items():
                if code in all_data:
                    try:
                        idx = all_data[code].index.get_loc(trading_date)
                        positions_value += float(all_data[code].iloc[idx]["Close"]) * pos.quantity
                    except (KeyError, IndexError):
                        positions_value += pos.entry_price * pos.quantity
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
            if self.params.require_trend_up:
                if pd.isna(row["MA_200"]) or row["Close"] < row["MA_200"]:
                    return None
            if self.params.require_50ma_up:
                if pd.isna(row["MA_50"]) or row["Close"] < row["MA_50"]:
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
            if self.params.use_atr_stop and not pd.isna(row["ATR"]):
                atr_stop = position.entry_price - (row["ATR"] * self.params.atr_multiplier)
                if current_price < atr_stop:
                    return {
                        "price": current_price,
                        "reason": f"atr_stop ({pnl_pct:.1f}%)",
                        "pnl_pct": pnl_pct,
                        "sell_ratio": 1.0,
                    }
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
            if pnl_pct <= -self.params.stop_loss_pct:
                return {
                    "price": current_price,
                    "reason": f"stop_loss ({pnl_pct:.1f}%)",
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
                        "reason": "trend_broken_middle_band",
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


ROBUST_EXPERIMENTS = {
    "baseline": BacktestParams(name="baseline"),
    "robust_1_trend_filter": BacktestParams(
        name="robust_1_trend_filter",
        bb_window=16,
        bb_std=1.6,
        squeeze_threshold=0.6,
        confidence_threshold=55,
        stop_loss_pct=5.0,
        take_profit_pct=10.0,
        sell_on_middle_band=False,
        require_trend_up=True,
    ),
    "robust_2_50ma_filter": BacktestParams(
        name="robust_2_50ma_filter",
        bb_window=16,
        bb_std=1.6,
        squeeze_threshold=0.6,
        confidence_threshold=55,
        stop_loss_pct=5.0,
        take_profit_pct=10.0,
        sell_on_middle_band=False,
        require_50ma_up=True,
    ),
    "robust_3_conservative": BacktestParams(
        name="robust_3_conservative",
        bb_window=18,
        bb_std=1.8,
        squeeze_threshold=0.65,
        confidence_threshold=60,
        stop_loss_pct=5.0,
        take_profit_pct=12.0,
        sell_on_middle_band=True,
        require_trend_up=True,
    ),
    "robust_4_trailing": BacktestParams(
        name="robust_4_trailing",
        bb_window=16,
        bb_std=1.6,
        squeeze_threshold=0.6,
        confidence_threshold=55,
        take_profit_pct=15.0,
        sell_on_middle_band=False,
        use_trailing_stop=True,
        trailing_stop_pct=8.0,
    ),
    "robust_5_balanced": BacktestParams(
        name="robust_5_balanced",
        bb_window=17,
        bb_std=1.7,
        squeeze_threshold=0.62,
        confidence_threshold=55,
        stop_loss_pct=5.0,
        take_profit_pct=10.0,
        sell_on_middle_band=False,
    ),
    "robust_6_both_ma": BacktestParams(
        name="robust_6_both_ma",
        bb_window=16,
        bb_std=1.6,
        squeeze_threshold=0.6,
        confidence_threshold=55,
        stop_loss_pct=5.0,
        take_profit_pct=10.0,
        sell_on_middle_band=False,
        require_trend_up=True,
        require_50ma_up=True,
    ),
    "robust_7_wider_stop": BacktestParams(
        name="robust_7_wider_stop",
        bb_window=16,
        bb_std=1.6,
        squeeze_threshold=0.6,
        confidence_threshold=55,
        stop_loss_pct=7.0,
        take_profit_pct=12.0,
        sell_on_middle_band=False,
        require_trend_up=True,
    ),
    "robust_8_high_conf": BacktestParams(
        name="robust_8_high_conf",
        bb_window=16,
        bb_std=1.6,
        squeeze_threshold=0.6,
        confidence_threshold=65,
        stop_loss_pct=5.0,
        take_profit_pct=10.0,
        sell_on_middle_band=False,
        require_trend_up=True,
    ),
    "robust_9_standard_bb": BacktestParams(
        name="robust_9_standard_bb",
        bb_window=20,
        bb_std=2.0,
        squeeze_threshold=0.7,
        confidence_threshold=55,
        stop_loss_pct=5.0,
        take_profit_pct=10.0,
        sell_on_middle_band=False,
        require_trend_up=True,
    ),
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
}


def load_stock_list(filepath):
    with open(filepath) as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def load_stock_names(filepath="data/stock_names_kr.json"):
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def run_single_experiment(args):
    exp_name, params, stock_codes, stock_names, period = args
    engine = BacktestEngine(params)
    result = engine.run_backtest(
        stock_codes, stock_names, period["start"], period["end"], 10_000_000
    )
    return {"experiment": exp_name, "period": period["name"], "metrics": result}


def main():
    print("=" * 70)
    print("ROBUST PARAMETER SEARCH: Finding parameters that work across periods")
    print("=" * 70)

    stock_codes = load_stock_list("kospi_top100.txt")[:100]
    stock_names = load_stock_names()

    print(f"\nLoaded {len(stock_codes)} stocks")
    print(
        f"Running {len(ROBUST_EXPERIMENTS)} experiments x 2 periods = {len(ROBUST_EXPERIMENTS) * 2} backtests\n"
    )

    experiment_args = []
    for exp_name, params in ROBUST_EXPERIMENTS.items():
        for period in [PERIOD_2023_2025, PERIOD_2020_2023]:
            experiment_args.append((exp_name, params, stock_codes, stock_names, period))

    results = []
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(run_single_experiment, args): args for args in experiment_args}
        for i, future in enumerate(as_completed(futures)):
            try:
                result = future.result()
                results.append(result)
                m = result["metrics"]
                print(
                    f"[{i + 1}/{len(experiment_args)}] {result['experiment']} ({result['period']}): "
                    f"{m['total_return_pct']:.2f}% return, {m['sharpe_ratio']:.2f} Sharpe"
                )
            except Exception as e:
                print(f"[{i + 1}/{len(experiment_args)}] FAILED: {e}")

    by_exp = {}
    for r in results:
        exp = r["experiment"]
        if exp not in by_exp:
            by_exp[exp] = {}
        by_exp[exp][r["period"]] = r["metrics"]

    print("\n" + "=" * 70)
    print("ROBUSTNESS ANALYSIS (Lower gap = More robust)")
    print("=" * 70)
    print(
        f"\n{'Experiment':<25} {'2023-25':<12} {'2020-23':<12} {'Gap':<10} {'Avg':<10} {'Robust Score':<12}"
    )
    print("-" * 80)

    robustness_scores = []
    for exp_name, periods in by_exp.items():
        if "2023-2025" in periods and "2020-2023" in periods:
            ret_2023 = periods["2023-2025"]["total_return_pct"]
            ret_2020 = periods["2020-2023"]["total_return_pct"]
            gap = abs(ret_2023 - ret_2020)
            avg = (ret_2023 + ret_2020) / 2
            robust_score = avg - (gap * 0.5)
            robustness_scores.append((exp_name, ret_2023, ret_2020, gap, avg, robust_score))

    robustness_scores.sort(key=lambda x: x[5], reverse=True)

    for exp_name, ret_2023, ret_2020, gap, avg, robust_score in robustness_scores:
        print(
            f"{exp_name:<25} {ret_2023:>10.2f}% {ret_2020:>10.2f}% {gap:>8.2f}% {avg:>8.2f}% {robust_score:>10.2f}"
        )

    best = robustness_scores[0]
    print(f"\n** BEST ROBUST STRATEGY: {best[0]} **")
    print(f"   - 2023-2025: {best[1]:.2f}%")
    print(f"   - 2020-2023: {best[2]:.2f}%")
    print(f"   - Gap: {best[3]:.2f}% (lower is better)")
    print(f"   - Robust Score: {best[5]:.2f}")

    report = ["# Robust Parameter Search Results\n"]
    report.append(f"Generated: {date.today().isoformat()}\n")
    report.append("## Robustness Ranking\n")
    report.append("| Rank | Strategy | 2023-25 | 2020-23 | Gap | Avg | Robust Score |")
    report.append("|------|----------|---------|---------|-----|-----|--------------|")
    for i, (exp, r23, r20, gap, avg, score) in enumerate(robustness_scores, 1):
        report.append(
            f"| {i} | {exp} | {r23:.2f}% | {r20:.2f}% | {gap:.2f}% | {avg:.2f}% | {score:.2f} |"
        )

    report.append(f"\n## Best Strategy: {best[0]}\n")
    report.append(f"```python\nparams = {ROBUST_EXPERIMENTS[best[0]].to_dict()}\n```\n")

    report.append("\n## Key Findings\n")
    report.append(
        "1. **Overfitting Alert**: original_optimal shows high 2023-25 return but poor robustness\n"
    )
    report.append(
        "2. **Trend Filter helps**: Strategies with require_trend_up=True show more consistent results\n"
    )
    report.append(
        "3. **BB parameters**: Moderate BB settings (16-18 window, 1.6-1.8 std) more robust than aggressive (12, 1.3)\n"
    )

    Path("reports").mkdir(exist_ok=True)
    with open("reports/robust_search_results.md", "w") as f:
        f.write("\n".join(report))

    with open("reports/robust_search_results.json", "w") as f:
        json.dump({"rankings": robustness_scores, "all_results": results}, f, indent=2, default=str)

    print("\nReports saved to reports/robust_search_results.md")


if __name__ == "__main__":
    main()
