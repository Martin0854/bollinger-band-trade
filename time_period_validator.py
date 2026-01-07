#!/usr/bin/env python3
"""
Time Period Validation: Test if optimal parameters work across 6-month and 1-year periods.
Validates temporal robustness by running backtests on multiple rolling windows.
"""

import json
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
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
    require_trend_up: bool = False
    name: str = "unnamed"

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}


class BacktestEngine:
    def __init__(self, params: BacktestParams):
        self.params = params
        self._data_cache = {}

    def run_backtest(
        self,
        stock_codes,
        stock_names,
        start_date,
        end_date,
        initial_capital=10_000_000,
        all_data=None,
    ):
        if all_data is None:
            all_data = self._fetch_all_data(stock_codes, start_date, end_date)

        processed_data = {}
        for code, df in all_data.items():
            processed_data[code] = calculate_all_indicators(
                df, self.params.bb_window, self.params.bb_std, self.params.squeeze_threshold
            )

        state = self._run_simulation(
            processed_data, stock_names, start_date, end_date, initial_capital
        )
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
            "final_value": final_value,
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
    "robust_standard_bb": BacktestParams(
        name="robust_standard_bb",
        bb_window=20,
        bb_std=2.0,
        squeeze_threshold=0.7,
        confidence_threshold=55,
        stop_loss_pct=5.0,
        take_profit_pct=10.0,
        sell_on_middle_band=False,
        require_trend_up=True,
    ),
    "moderate_optimal": BacktestParams(
        name="moderate_optimal",
        bb_window=16,
        bb_std=1.6,
        squeeze_threshold=0.6,
        confidence_threshold=55,
        stop_loss_pct=5.0,
        take_profit_pct=10.0,
        sell_on_middle_band=False,
        require_trend_up=True,
    ),
}


def generate_time_periods():
    """Generate rolling 6-month and 1-year periods from 2020 to 2025."""
    periods = []

    for year in [2020, 2021, 2022, 2023, 2024, 2025]:
        periods.append(
            {"start": date(year, 1, 1), "end": date(year, 6, 30), "name": f"{year}H1", "type": "6M"}
        )
        if year < 2025 or date.today() > date(2025, 7, 1):
            periods.append(
                {
                    "start": date(year, 7, 1),
                    "end": date(year, 12, 31),
                    "name": f"{year}H2",
                    "type": "6M",
                }
            )

    for year in [2020, 2021, 2022, 2023, 2024, 2025]:
        end_date = min(date(year, 12, 31), date.today())
        if end_date > date(year, 6, 1):
            periods.append(
                {"start": date(year, 1, 1), "end": end_date, "name": f"{year}", "type": "1Y"}
            )

    periods.append(
        {"start": date(2023, 1, 1), "end": date(2025, 12, 31), "name": "2023-2025", "type": "3Y"}
    )
    periods.append(
        {"start": date(2020, 1, 1), "end": date(2023, 12, 31), "name": "2020-2023", "type": "4Y"}
    )

    return periods


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
        "start": str(period["start"]),
        "end": str(period["end"]),
        "metrics": result,
    }


def main():
    print("=" * 70)
    print("TIME PERIOD VALIDATION: Testing strategies on 6M, 1Y, 3Y periods")
    print("=" * 70)

    stock_codes = load_stock_list("kospi_top100.txt")[:100]
    stock_names = load_stock_names()

    periods = generate_time_periods()
    print(f"\nLoaded {len(stock_codes)} stocks")
    print(
        f"Testing {len(STRATEGIES)} strategies x {len(periods)} periods = {len(STRATEGIES) * len(periods)} backtests\n"
    )

    experiment_args = []
    for strategy_name, params in STRATEGIES.items():
        for period in periods:
            experiment_args.append((strategy_name, params, stock_codes, stock_names, period))

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
                    f"{m['total_return_pct']:.2f}% return, {m['sharpe_ratio']:.2f} Sharpe, {m['total_trades']} trades"
                )
            except Exception as e:
                print(f"[{i + 1}/{len(experiment_args)}] FAILED: {e}")

    generate_report(results, periods)


def generate_report(results, periods):
    Path("reports").mkdir(exist_ok=True)

    by_strategy = {}
    for r in results:
        strat = r["strategy"]
        if strat not in by_strategy:
            by_strategy[strat] = {}
        by_strategy[strat][r["period"]] = r["metrics"]

    report = ["# Time Period Validation Report\n"]
    report.append(f"Generated: {date.today().isoformat()}\n")

    report.append("## Summary by Period Type\n")
    for period_type in ["6M", "1Y", "3Y", "4Y"]:
        type_periods = [p for p in periods if p["type"] == period_type]
        if not type_periods:
            continue

        report.append(f"\n### {period_type} Periods\n")
        report.append("| Strategy | Period | Return | Sharpe | MDD | Win Rate | Trades |")
        report.append("|----------|--------|--------|--------|-----|----------|--------|")

        for strat_name, strat_results in by_strategy.items():
            for p in type_periods:
                if p["name"] in strat_results:
                    m = strat_results[p["name"]]
                    report.append(
                        f"| {strat_name} | {p['name']} | {m['total_return_pct']:.2f}% | "
                        f"{m['sharpe_ratio']:.2f} | {m['max_drawdown']:.2f}% | "
                        f"{m['win_rate']:.1f}% | {m['total_trades']} |"
                    )

    report.append("\n## Strategy Performance Comparison\n")
    report.append("### Average Performance by Strategy (6-Month Periods)\n")
    report.append("| Strategy | Avg Return | Avg Sharpe | Positive Periods | Consistency |")
    report.append("|----------|------------|------------|------------------|-------------|")

    for strat_name, strat_results in by_strategy.items():
        six_month_results = {k: v for k, v in strat_results.items() if "H1" in k or "H2" in k}
        if six_month_results:
            returns = [v["total_return_pct"] for v in six_month_results.values()]
            sharpes = [v["sharpe_ratio"] for v in six_month_results.values()]
            positive = sum(1 for r in returns if r > 0)
            avg_ret = np.mean(returns)
            avg_sharpe = np.mean(sharpes)
            consistency = (positive / len(returns)) * 100
            report.append(
                f"| {strat_name} | {avg_ret:.2f}% | {avg_sharpe:.2f} | {positive}/{len(returns)} | {consistency:.0f}% |"
            )

    report.append("\n### Average Performance by Strategy (1-Year Periods)\n")
    report.append("| Strategy | Avg Return | Avg Sharpe | Positive Periods | Consistency |")
    report.append("|----------|------------|------------|------------------|-------------|")

    for strat_name, strat_results in by_strategy.items():
        one_year_results = {k: v for k, v in strat_results.items() if k.isdigit() and len(k) == 4}
        if one_year_results:
            returns = [v["total_return_pct"] for v in one_year_results.values()]
            sharpes = [v["sharpe_ratio"] for v in one_year_results.values()]
            positive = sum(1 for r in returns if r > 0)
            avg_ret = np.mean(returns)
            avg_sharpe = np.mean(sharpes)
            consistency = (positive / len(returns)) * 100
            report.append(
                f"| {strat_name} | {avg_ret:.2f}% | {avg_sharpe:.2f} | {positive}/{len(returns)} | {consistency:.0f}% |"
            )

    report.append("\n## Key Findings\n")

    six_month_perf = {}
    for strat_name, strat_results in by_strategy.items():
        six_month_results = {k: v for k, v in strat_results.items() if "H1" in k or "H2" in k}
        if six_month_results:
            returns = [v["total_return_pct"] for v in six_month_results.values()]
            positive_ratio = sum(1 for r in returns if r > 0) / len(returns)
            six_month_perf[strat_name] = {"avg": np.mean(returns), "consistency": positive_ratio}

    if six_month_perf:
        best_consistency = max(six_month_perf.items(), key=lambda x: x[1]["consistency"])
        best_return = max(six_month_perf.items(), key=lambda x: x[1]["avg"])
        report.append(
            f"1. **Most Consistent (6M)**: {best_consistency[0]} ({best_consistency[1]['consistency'] * 100:.0f}% positive periods)"
        )
        report.append(
            f"2. **Highest Avg Return (6M)**: {best_return[0]} ({best_return[1]['avg']:.2f}% avg return)"
        )

    with open("reports/time_period_validation.md", "w") as f:
        f.write("\n".join(report))

    with open("reports/time_period_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("\nReports saved to reports/time_period_validation.md")


if __name__ == "__main__":
    main()
