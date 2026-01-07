#!/usr/bin/env python
"""
2025년 Daily Wizard 알고리즘 백테스트

Daily Wizard와 동일한 로직으로 2025년 1년간 시뮬레이션 실행
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import warnings

import pandas as pd
import numpy as np
import yfinance as yf

warnings.filterwarnings("ignore")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


# ============================================================================
# Configuration (optimized via time-period validation 2026-01-08)
# ============================================================================
INITIAL_CAPITAL = 1_000_000
MAX_POSITIONS = 15
MAX_POSITION_PERCENT = 10.0

BB_WINDOW = 12
BB_STD = 1.3
SQUEEZE_THRESHOLD = 0.55
CONFIDENCE_THRESHOLD = 50
STOP_LOSS_PERCENT = 4.5
TAKE_PROFIT_PERCENT = 9.0
MARKET_FILTER_ENABLED = True
MARKET_FILTER_MA = 200

DEFAULT_START_DATE = "2025-01-02"
DEFAULT_END_DATE = "2025-12-31"


# ============================================================================
# Data Classes
# ============================================================================
@dataclass
class Position:
    stock_code: str
    stock_name: str
    quantity: int
    entry_price: float
    entry_date: str

    @property
    def cost_basis(self) -> float:
        return self.entry_price * self.quantity


@dataclass
class Trade:
    date: str
    stock_code: str
    stock_name: str
    action: str  # BUY or SELL
    price: float
    quantity: int
    reason: str
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None


@dataclass
class BacktestState:
    cash: float
    positions: Dict[str, Position] = field(default_factory=dict)
    trades: List[Trade] = field(default_factory=list)
    daily_values: List[tuple] = field(default_factory=list)  # (date, value)


# ============================================================================
# Data Loading
# ============================================================================
def load_stock_names() -> Dict[str, str]:
    """Load Korean stock names from JSON file."""
    import json

    path = Path(__file__).parent / "data" / "stock_names_kr.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_kospi_top100(stock_file: str = "kospi_top100.txt") -> List[str]:
    """Load KOSPI Top 100 stock codes."""
    path = Path(__file__).parent / stock_file
    with open(path, "r") as f:
        stocks = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return stocks[:100]


def fetch_all_data(
    stock_codes: List[str], start_date: str, end_date: str
) -> Dict[str, pd.DataFrame]:
    """Fetch all stock data upfront for faster backtesting."""
    print(f"\n[1] Fetching data for {len(stock_codes)} stocks...")

    # Add buffer for indicator calculation
    start_dt = datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=60)
    start_with_buffer = start_dt.strftime("%Y-%m-%d")

    all_data = {}
    failed = []

    for i, code in enumerate(stock_codes):
        print(f"\r    Loading {i + 1}/{len(stock_codes)}: {code}    ", end="")

        ticker = f"{code}.KS"
        try:
            df = yf.download(
                ticker, start=start_with_buffer, end=end_date, progress=False, auto_adjust=False
            )

            if df.empty:
                ticker = f"{code}.KQ"
                df = yf.download(
                    ticker, start=start_with_buffer, end=end_date, progress=False, auto_adjust=False
                )

            if not df.empty and len(df) >= 30:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                all_data[code] = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
            else:
                failed.append(code)
        except Exception:
            failed.append(code)

    print(f"\r    Loaded {len(all_data)} stocks, {len(failed)} failed            ")
    return all_data


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all technical indicators."""
    df = df.copy()
    close = df["Close"]
    volume = df["Volume"]

    sma = close.rolling(window=BB_WINDOW).mean()
    std = close.rolling(window=BB_WINDOW).std()
    df["BB_Upper"] = sma + (std * BB_STD)
    df["BB_Middle"] = sma
    df["BB_Lower"] = sma - (std * BB_STD)
    df["BB_Width"] = (df["BB_Upper"] - df["BB_Lower"]) / sma * 100
    df["BB_Width_MA"] = df["BB_Width"].rolling(window=10).mean()

    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9).mean()
    df["MACD_Histogram"] = df["MACD"] - df["MACD_Signal"]

    df["Volume_MA"] = volume.rolling(window=20).mean()
    df["Volume_Ratio"] = volume / df["Volume_MA"]

    df["In_Squeeze"] = df["BB_Width"] < (df["BB_Width_MA"] * SQUEEZE_THRESHOLD)

    df["MA_200"] = close.rolling(window=MARKET_FILTER_MA).mean()

    return df


def calculate_confidence(row: pd.Series) -> float:
    """
    Calculate confidence score for a signal (continuous scoring).

    Scoring (0-100):
        - Base (Bollinger breakout): 25 points
        - Volume (0-25): Linear scale from 1.0x to 2.0x
        - RSI (0-20): Peak at 50, decreases toward 30/70
        - MACD (0-30): Based on histogram strength relative to signal
    """
    score = 25.0  # Base score for Bollinger breakout

    # Volume Score (0-25점)
    # 1.0x -> 0점, 1.5x -> 12.5점, 2.0x -> 25점 (cap)
    vol_ratio = row["Volume_Ratio"]
    if vol_ratio > 1.0:
        vol_score = min(25.0, (vol_ratio - 1.0) * 25.0)
        score += vol_score

    # RSI Score (0-20점)
    # 50이 최적(20점), 30/70에서 0점, 범위 밖은 0점
    rsi = row["RSI"]
    if 30 <= rsi <= 70:
        distance = abs(rsi - 50)
        rsi_score = 20.0 * (1 - distance / 20.0)
        score += rsi_score

    # MACD Score (0-30점)
    # Histogram이 양수일 때, Signal 대비 비율로 점수 계산
    macd_hist = row["MACD_Histogram"]
    if macd_hist > 0:
        macd_signal = abs(row["MACD_Signal"]) if row["MACD_Signal"] != 0 else 0.001
        # histogram/signal 비율: 0.5 이상이면 만점
        macd_ratio = min(macd_hist / macd_signal, 1.0)
        macd_score = 30.0 * macd_ratio
        score += macd_score

    return score


# ============================================================================
# Trading Logic
# ============================================================================
def check_buy_signal(df: pd.DataFrame, date: str) -> Optional[dict]:
    """Check if there's a buy signal on given date."""
    try:
        idx = df.index.get_loc(pd.Timestamp(date))
        if idx < 30:
            return None

        row = df.iloc[idx]
        prev_rows = df.iloc[idx - 5 : idx]

        if pd.isna(row["BB_Upper"]) or pd.isna(row["RSI"]):
            return None

        if MARKET_FILTER_ENABLED and not pd.isna(row["MA_200"]):
            if row["Close"] < row["MA_200"]:
                return None

        price_breakout = row["Close"] > row["BB_Upper"]

        was_in_squeeze = prev_rows["In_Squeeze"].any()
        bandwidth_expanding = row["BB_Width"] > df.iloc[idx - 1]["BB_Width"]

        if price_breakout and (was_in_squeeze or bandwidth_expanding):
            confidence = calculate_confidence(row)
            if confidence >= CONFIDENCE_THRESHOLD:
                return {
                    "price": float(row["Close"]),
                    "confidence": confidence,
                    "indicators": {
                        "rsi": float(row["RSI"]),
                        "macd": float(row["MACD_Histogram"]),
                        "volume_ratio": float(row["Volume_Ratio"]),
                        "above_ma200": bool(row["Close"] > row["MA_200"])
                        if not pd.isna(row["MA_200"])
                        else None,
                    },
                }
    except (KeyError, IndexError):
        pass

    return None


def check_sell_signal(df: pd.DataFrame, date: str, entry_price: float) -> Optional[dict]:
    """Check if there's a sell signal on given date."""
    try:
        idx = df.index.get_loc(pd.Timestamp(date))
        row = df.iloc[idx]

        current_price = float(row["Close"])
        pnl_pct = ((current_price - entry_price) / entry_price) * 100

        if pnl_pct <= -STOP_LOSS_PERCENT:
            return {
                "price": current_price,
                "reason": f"stop_loss ({pnl_pct:.1f}%)",
                "pnl_pct": pnl_pct,
            }

        if pnl_pct >= TAKE_PROFIT_PERCENT:
            return {
                "price": current_price,
                "reason": f"take_profit ({pnl_pct:+.1f}%)",
                "pnl_pct": pnl_pct,
            }

        if current_price < row["BB_Lower"]:
            return {
                "price": current_price,
                "reason": f"lower_band_touch ({pnl_pct:+.1f}%)",
                "pnl_pct": pnl_pct,
            }
    except (KeyError, IndexError):
        pass

    return None


def calculate_position_size(price: float, cash: float) -> int:
    """Calculate position size based on risk management rules."""
    max_allocation = INITIAL_CAPITAL * (MAX_POSITION_PERCENT / 100)
    max_shares = int(max_allocation / price)

    # Also check available cash
    affordable_shares = int(cash / price)

    return min(max_shares, affordable_shares)


# ============================================================================
# Backtest Engine
# ============================================================================
def run_backtest(
    all_data: Dict[str, pd.DataFrame],
    stock_names: Dict[str, str],
    start_date: str,
    end_date: str,
) -> BacktestState:
    """Run the backtest simulation."""

    state = BacktestState(cash=INITIAL_CAPITAL)

    # Pre-calculate indicators for all stocks
    print("\n[2] Calculating indicators...")
    for code in all_data:
        all_data[code] = calculate_indicators(all_data[code])

    # Get trading days
    sample_df = list(all_data.values())[0]
    trading_days = sample_df.loc[start_date:end_date].index.tolist()

    print(f"\n[3] Running backtest: {start_date} ~ {end_date}")
    print(f"    Trading days: {len(trading_days)}")
    print(f"    Initial capital: {INITIAL_CAPITAL:,} KRW")
    print()

    for i, date in enumerate(trading_days):
        date_str = date.strftime("%Y-%m-%d")

        if i % 20 == 0:
            print(f"\r    Processing: {date_str}    ", end="")

        # 1. Check SELL signals for existing positions
        positions_to_sell = []
        for code, pos in state.positions.items():
            if code not in all_data:
                continue

            signal = check_sell_signal(all_data[code], date_str, pos.entry_price)
            if signal:
                positions_to_sell.append((code, signal))

        # Execute sells
        for code, signal in positions_to_sell:
            pos = state.positions[code]
            proceeds = signal["price"] * pos.quantity
            pnl = (signal["price"] - pos.entry_price) * pos.quantity

            state.cash += proceeds
            state.trades.append(
                Trade(
                    date=date_str,
                    stock_code=code,
                    stock_name=pos.stock_name,
                    action="SELL",
                    price=signal["price"],
                    quantity=pos.quantity,
                    reason=signal["reason"],
                    pnl=pnl,
                    pnl_pct=signal["pnl_pct"],
                )
            )
            del state.positions[code]

        # 2. Check BUY signals for stocks not in portfolio
        if len(state.positions) < MAX_POSITIONS:
            buy_candidates = []

            for code, df in all_data.items():
                if code in state.positions:
                    continue

                signal = check_buy_signal(df, date_str)
                if signal:
                    buy_candidates.append((code, signal))

            # Sort by confidence
            buy_candidates.sort(key=lambda x: x[1]["confidence"], reverse=True)

            # Execute buys
            for code, signal in buy_candidates:
                if len(state.positions) >= MAX_POSITIONS:
                    break

                quantity = calculate_position_size(signal["price"], state.cash)
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
                )
                state.trades.append(
                    Trade(
                        date=date_str,
                        stock_code=code,
                        stock_name=stock_names.get(code, code),
                        action="BUY",
                        price=signal["price"],
                        quantity=quantity,
                        reason=f"squeeze_breakout (conf:{signal['confidence']})",
                    )
                )

        # 3. Calculate daily portfolio value
        positions_value = 0
        for code, pos in state.positions.items():
            if code in all_data:
                try:
                    idx = all_data[code].index.get_loc(date)
                    current_price = float(all_data[code].iloc[idx]["Close"])
                    positions_value += current_price * pos.quantity
                except (KeyError, IndexError):
                    positions_value += pos.entry_price * pos.quantity

        total_value = state.cash + positions_value
        state.daily_values.append((date_str, total_value))

    print(f"\r    Completed: {len(trading_days)} trading days processed    ")

    return state


# ============================================================================
# Performance Analysis
# ============================================================================
def analyze_performance(state: BacktestState) -> dict:
    """Analyze backtest performance."""

    # Basic metrics
    final_value = state.daily_values[-1][1] if state.daily_values else INITIAL_CAPITAL
    total_return = ((final_value - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100

    # Trade analysis
    sell_trades = [t for t in state.trades if t.action == "SELL"]
    winning_trades = [t for t in sell_trades if t.pnl and t.pnl > 0]
    losing_trades = [t for t in sell_trades if t.pnl and t.pnl <= 0]

    win_rate = (len(winning_trades) / len(sell_trades) * 100) if sell_trades else 0

    total_pnl = sum(t.pnl for t in sell_trades if t.pnl)
    avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
    avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0

    # Drawdown
    values = [v[1] for v in state.daily_values]
    if values:
        peak = values[0]
        max_drawdown = 0
        for v in values:
            if v > peak:
                peak = v
            drawdown = (peak - v) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)
    else:
        max_drawdown = 0

    # Monthly returns
    df_values = pd.DataFrame(state.daily_values, columns=["date", "value"])
    df_values["date"] = pd.to_datetime(df_values["date"])
    df_values.set_index("date", inplace=True)

    monthly_returns = df_values.resample("M").last()
    monthly_returns["return"] = monthly_returns["value"].pct_change() * 100

    return {
        "initial_capital": INITIAL_CAPITAL,
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
        "monthly_returns": monthly_returns,
    }


def print_results(state: BacktestState, metrics: dict):
    """Print backtest results."""

    print("\n" + "=" * 70)
    print("2025년 Daily Wizard 백테스트 결과")
    print("=" * 70)

    print(f"\n[포트폴리오 성과]")
    print(f"  시작 금액:        {metrics['initial_capital']:>15,} KRW")
    print(f"  최종 금액:        {metrics['final_value']:>15,.0f} KRW")

    ret = metrics["total_return_pct"]
    ret_str = f"+{ret:.2f}%" if ret >= 0 else f"{ret:.2f}%"
    print(f"  총 수익률:        {ret_str:>15}")
    print(f"  최대 낙폭:        {metrics['max_drawdown']:>14.2f}%")

    print(f"\n[거래 통계]")
    print(f"  총 거래 수:       {metrics['total_trades']:>15}")
    print(f"  매수 거래:        {metrics['buy_trades']:>15}")
    print(f"  매도 거래:        {metrics['sell_trades']:>15}")
    print(f"  승리 거래:        {metrics['winning_trades']:>15}")
    print(f"  패배 거래:        {metrics['losing_trades']:>15}")
    print(f"  승률:             {metrics['win_rate']:>14.1f}%")

    print(f"\n[손익 분석]")
    print(f"  실현 손익:        {metrics['total_pnl']:>+15,.0f} KRW")
    print(f"  평균 수익 (승):   {metrics['avg_win']:>+15,.0f} KRW")
    print(f"  평균 손실 (패):   {metrics['avg_loss']:>+15,.0f} KRW")

    # Monthly returns
    print(f"\n[월별 수익률]")
    print("-" * 40)
    monthly = metrics["monthly_returns"]
    for idx, row in monthly.iterrows():
        if pd.notna(row["return"]):
            month_str = idx.strftime("%Y-%m")
            ret = row["return"]
            ret_indicator = "+" if ret >= 0 else ""
            bar = "█" * int(abs(ret) / 2) if abs(ret) > 0 else ""
            color_bar = f"{'🟢' if ret >= 0 else '🔴'} {bar}"
            print(f"  {month_str}: {ret_indicator}{ret:>6.2f}% {color_bar}")

    # Recent trades
    print(f"\n[최근 거래 내역]")
    print("-" * 70)
    recent_trades = state.trades[-10:]
    for t in recent_trades:
        pnl_str = ""
        if t.pnl is not None:
            pnl_str = f" (PnL: {t.pnl:+,.0f})"
        print(
            f"  {t.date} {t.action:4} {t.stock_code} ({t.stock_name[:8]:<8}) "
            f"x{t.quantity} @ {t.price:,.0f}{pnl_str}"
        )

    # Current positions
    if state.positions:
        print(f"\n[최종 보유 종목]")
        print("-" * 70)
        for code, pos in state.positions.items():
            print(
                f"  {pos.stock_code} ({pos.stock_name}) "
                f"x{pos.quantity} @ {pos.entry_price:,.0f} (매수일: {pos.entry_date})"
            )

    print("\n" + "=" * 70)


# ============================================================================
# Main
# ============================================================================
def save_to_json(
    state: BacktestState,
    metrics: dict,
    output_file: str = "backtest_2025_result.json",
    start_date: str = None,
    end_date: str = None,
    all_data: Dict[str, pd.DataFrame] = None,
):
    """Save backtest results to JSON file in portfolio_state.json format."""
    import json
    from datetime import datetime

    # Get final prices for positions
    def get_final_price(stock_code: str) -> float:
        if all_data and stock_code in all_data:
            df = all_data[stock_code]
            if end_date and end_date in df.index.strftime("%Y-%m-%d").tolist():
                return float(df.loc[end_date]["Close"])
            elif not df.empty:
                return float(df["Close"].iloc[-1])
        return None

    # Convert positions to dict format with current_price
    positions = []
    for pos in state.positions.values():
        pos_dict = {
            "stock_code": pos.stock_code,
            "stock_name": pos.stock_name,
            "quantity": pos.quantity,
            "entry_price": pos.entry_price,
            "entry_date": pos.entry_date,
            "entry_reason": "squeeze_breakout_buy",
        }
        final_price = get_final_price(pos.stock_code)
        if final_price:
            pos_dict["current_price"] = final_price
        positions.append(pos_dict)

    # Convert trades to dict format
    trade_history = [
        {
            "date": t.date,
            "stock_code": t.stock_code,
            "stock_name": t.stock_name,
            "action": t.action,
            "price": t.price,
            "quantity": t.quantity,
            "reason": t.reason,
            "realized_pnl": t.pnl,
        }
        for t in state.trades
    ]

    # Build output structure
    result = {
        "initial_capital": INITIAL_CAPITAL,
        "cash_balance": state.cash,
        "start_date": start_date or DEFAULT_START_DATE,
        "end_date": end_date or DEFAULT_END_DATE,
        "last_updated": datetime.now().isoformat(),
        "positions": positions,
        "trade_history": trade_history,
        "pending_orders": [],
        "last_run_output": "",
        "backtest_metrics": {
            "final_value": metrics["final_value"],
            "total_return_pct": metrics["total_return_pct"],
            "total_trades": metrics["total_trades"],
            "buy_trades": metrics["buy_trades"],
            "sell_trades": metrics["sell_trades"],
            "winning_trades": metrics["winning_trades"],
            "losing_trades": metrics["losing_trades"],
            "win_rate": metrics["win_rate"],
            "total_pnl": metrics["total_pnl"],
            "avg_win": metrics["avg_win"],
            "avg_loss": metrics["avg_loss"],
            "max_drawdown": metrics["max_drawdown"],
        },
        "daily_values": [{"date": d, "value": v} for d, v in state.daily_values],
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n결과가 저장되었습니다: {output_file}")


def main(
    stock_file: str = "kospi_top100.txt",
    output_file: str = "backtest_result.json",
    start_date: str = None,
    end_date: str = None,
):
    start_date = start_date or DEFAULT_START_DATE
    end_date = end_date or DEFAULT_END_DATE
    year = start_date[:4]

    print("=" * 70)
    print(f"{year}년 Daily Wizard 알고리즘 백테스트")
    print("=" * 70)
    print(f"\n설정:")
    print(f"  기간: {start_date} ~ {end_date}")
    print(f"  초기 자본: {INITIAL_CAPITAL:,} KRW")
    print(f"  최대 포지션: {MAX_POSITIONS}개")
    print(f"  포지션당 비중: {MAX_POSITION_PERCENT}%")
    print(f"  Confidence 임계값: {CONFIDENCE_THRESHOLD}")
    print(f"  손절: -{STOP_LOSS_PERCENT}%")
    print(f"  종목 리스트: {stock_file}")

    # Load data
    stock_codes = load_kospi_top100(stock_file)
    stock_names = load_stock_names()
    all_data = fetch_all_data(stock_codes, start_date, end_date)

    # Run backtest
    state = run_backtest(all_data, stock_names, start_date, end_date)

    # Analyze and print results
    metrics = analyze_performance(state)
    print_results(state, metrics)

    # Save to JSON
    save_to_json(state, metrics, output_file, start_date, end_date, all_data)

    return state, metrics


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="연도별 백테스트")
    parser.add_argument("--stocks", default="kospi_top100.txt", help="종목 리스트 파일")
    parser.add_argument("--output", default="backtest_result.json", help="결과 JSON 파일")
    parser.add_argument("--start", default=DEFAULT_START_DATE, help="시작일 (YYYY-MM-DD)")
    parser.add_argument("--end", default=DEFAULT_END_DATE, help="종료일 (YYYY-MM-DD)")
    parser.add_argument("--year", type=int, help="연도 (시작/종료일 자동 설정)")
    args = parser.parse_args()

    # Year shortcut
    if args.year:
        args.start = f"{args.year}-01-02"
        args.end = f"{args.year}-12-31"
        if args.output == "backtest_result.json":
            args.output = f"backtest_{args.year}_result.json"

    state, metrics = main(args.stocks, args.output, args.start, args.end)
