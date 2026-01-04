#!/usr/bin/env python
"""
Portfolio State JSON 시각화 도구

portfolio_state.json 파일을 읽어 보기 좋게 시각화합니다.

Usage:
    python visualize_portfolio.py [--file PATH]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

import yfinance as yf


def fetch_current_prices(stock_codes: list) -> Dict[str, float]:
    """Fetch current prices for given stock codes using yfinance."""
    prices = {}
    for code in stock_codes:
        try:
            ticker = yf.Ticker(f"{code}.KS")
            hist = ticker.history(period="5d")
            if not hist.empty:
                prices[code] = hist["Close"].iloc[-1]
        except Exception:
            pass
    return prices


def load_portfolio(file_path: str) -> dict:
    """Load portfolio state from JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_number(n: float, is_currency: bool = True) -> str:
    """Format number with comma separators."""
    if is_currency:
        return f"{n:,.0f}"
    return f"{n:,.2f}"


def format_pct(pct: float) -> str:
    """Format percentage with sign."""
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.2f}%"


def print_header(title: str, width: int = 70):
    """Print section header."""
    print("\n" + "=" * width)
    print(f" {title}")
    print("=" * width)


def print_subheader(title: str, width: int = 70):
    """Print subsection header."""
    print("\n" + "-" * width)
    print(f" {title}")
    print("-" * width)


def visualize_summary(data: dict, current_prices: Dict[str, float] = None):
    """Visualize portfolio summary."""
    print_header("포트폴리오 요약")

    initial = data.get("initial_capital", 0)
    cash = data.get("cash_balance", 0)
    start_date = data.get("start_date", "N/A")
    last_updated = data.get("last_updated", "N/A")

    # Parse last_updated
    if last_updated and last_updated != "N/A":
        try:
            dt = datetime.fromisoformat(last_updated)
            last_updated = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            pass

    # Calculate positions value
    positions = data.get("positions", [])
    cost_basis = sum(p.get("entry_price", 0) * p.get("quantity", 0) for p in positions)

    # Calculate current value using current prices
    if current_prices:
        current_value = sum(
            current_prices.get(p.get("stock_code", ""), p.get("entry_price", 0)) * p.get("quantity", 0)
            for p in positions
        )
        unrealized_pnl = current_value - cost_basis
    else:
        current_value = cost_basis
        unrealized_pnl = 0

    # Total value and return
    total_value = cash + current_value
    total_return = ((total_value - initial) / initial * 100) if initial > 0 else 0

    print(f"\n  시작일:           {start_date}")
    print(f"  마지막 업데이트:  {last_updated}")
    print()
    print(f"  초기 자본:        {format_number(initial):>15} KRW")
    print(f"  현금 잔고:        {format_number(cash):>15} KRW")
    print(f"  보유 종목 원가:   {format_number(cost_basis):>15} KRW")
    if current_prices:
        print(f"  보유 종목 평가:   {format_number(current_value):>15} KRW")
        pnl_str = f"{'+' if unrealized_pnl >= 0 else ''}{format_number(unrealized_pnl)}"
        print(f"  미실현 손익:      {pnl_str:>15} KRW")
    print(f"  ──────────────────────────────────────")
    print(f"  총 평가액:        {format_number(total_value):>15} KRW")
    print(f"  총 수익률:        {format_pct(total_return):>15}")
    print(f"\n  보유 종목 수:     {len(positions):>15}개")


def visualize_positions(data: dict, current_prices: Dict[str, float] = None):
    """Visualize current positions with unrealized P&L."""
    positions = data.get("positions", [])

    if not positions:
        print_subheader("보유 종목")
        print("\n  보유 중인 종목이 없습니다.")
        return

    print_subheader(f"보유 종목 ({len(positions)}개)")

    if current_prices:
        # Header with current price and P&L
        print(f"\n  {'종목코드':<8} {'종목명':<10} {'수량':>4} {'매수가':>9} {'현재가':>9} {'평가손익':>12} {'수익률':>8}")
        print("  " + "-" * 74)

        total_cost = 0
        total_current = 0
        total_pnl = 0

        for pos in positions:
            code = pos.get("stock_code", "")
            name = pos.get("stock_name", "")[:8]
            qty = pos.get("quantity", 0)
            entry = pos.get("entry_price", 0)
            current = current_prices.get(code, entry)

            cost = entry * qty
            current_val = current * qty
            pnl = current_val - cost
            pnl_pct = ((current - entry) / entry * 100) if entry > 0 else 0

            total_cost += cost
            total_current += current_val
            total_pnl += pnl

            pnl_str = f"{'+' if pnl >= 0 else ''}{pnl:,.0f}"
            pct_str = f"{'+' if pnl_pct >= 0 else ''}{pnl_pct:.1f}%"

            print(f"  {code:<8} {name:<10} {qty:>4} {entry:>9,.0f} {current:>9,.0f} {pnl_str:>12} {pct_str:>8}")

        print("  " + "-" * 74)
        total_pnl_str = f"{'+' if total_pnl >= 0 else ''}{total_pnl:,.0f}"
        total_pct = ((total_current - total_cost) / total_cost * 100) if total_cost > 0 else 0
        total_pct_str = f"{'+' if total_pct >= 0 else ''}{total_pct:.1f}%"
        print(f"  {'합계':<8} {'':<10} {'':<4} {total_cost:>9,.0f} {total_current:>9,.0f} {total_pnl_str:>12} {total_pct_str:>8}")
    else:
        # Header without current prices (fallback)
        print(f"\n  {'종목코드':<8} {'종목명':<12} {'수량':>6} {'매수가':>10} {'매수금액':>12} {'매수일':>12}")
        print("  " + "-" * 66)

        total_cost = 0
        for pos in positions:
            code = pos.get("stock_code", "")
            name = pos.get("stock_name", "")[:10]
            qty = pos.get("quantity", 0)
            price = pos.get("entry_price", 0)
            date = pos.get("entry_date", "")
            cost = price * qty
            total_cost += cost

            print(f"  {code:<8} {name:<12} {qty:>6} {format_number(price):>10} {format_number(cost):>12} {date:>12}")

        print("  " + "-" * 66)
        print(f"  {'합계':<8} {'':<12} {'':<6} {'':<10} {format_number(total_cost):>12}")


def visualize_pending_orders(data: dict):
    """Visualize pending orders with detailed reasons."""
    orders = data.get("pending_orders", [])

    if not orders:
        print_subheader("대기 중인 주문")
        print("\n  대기 중인 주문이 없습니다.")
        return

    print_subheader(f"대기 중인 주문 ({len(orders)}개)")

    for i, order in enumerate(orders, 1):
        action = order.get("action", "")
        code = order.get("stock_code", "")
        name = order.get("stock_name", "")
        price = order.get("recommended_price", 0)
        qty = order.get("quantity", 0)
        executed = order.get("executed", False)
        actual = order.get("actual_price")

        # Status indicator
        if executed:
            status = "✅ 체결완료"
        elif actual:
            status = "⏳ 가격입력됨"
        else:
            status = "⬜ 대기중"

        # Color for action
        action_str = f"🔴 {action}" if action == "SELL" else f"🟢 {action}"

        print(f"\n  [{i}] {action_str} {code} ({name})")
        print(f"      추천가: {format_number(price)} KRW × {qty}주 = {format_number(price * qty)} KRW")
        print(f"      상태: {status}")

        if actual:
            print(f"      실제 체결가: {format_number(actual)} KRW")

        # Show reason detail
        reason = order.get("reason_detail", "")
        if reason:
            print(f"\n      ─── 판단 근거 ───")
            for line in reason.split("\n"):
                print(f"      {line}")

        # Show indicators
        indicators = order.get("indicators", {})
        if indicators:
            print(f"\n      ─── 기술 지표 ───")
            for key, value in indicators.items():
                if isinstance(value, float):
                    print(f"      {key}: {value:.4f}")
                else:
                    print(f"      {key}: {value}")


def visualize_trade_history(data: dict):
    """Visualize trade history."""
    trades = data.get("trade_history", [])

    if not trades:
        print_subheader("거래 내역")
        print("\n  거래 내역이 없습니다.")
        return

    print_subheader(f"거래 내역 ({len(trades)}건)")

    # Summary
    buys = [t for t in trades if t.get("action") == "BUY"]
    sells = [t for t in trades if t.get("action") == "SELL"]
    total_pnl = sum(t.get("realized_pnl", 0) or 0 for t in sells)

    print(f"\n  매수: {len(buys)}건, 매도: {len(sells)}건")
    print(f"  실현 손익: {format_number(total_pnl)} KRW")

    # Recent trades (last 10)
    print(f"\n  최근 거래:")
    print(f"  {'일자':<12} {'종류':>6} {'종목':>10} {'가격':>10} {'수량':>6} {'손익':>12}")
    print("  " + "-" * 62)

    for trade in trades[-10:]:
        date = trade.get("date", "")
        action = trade.get("action", "")
        code = trade.get("stock_code", "")
        price = trade.get("price", 0)
        qty = trade.get("quantity", 0)
        pnl = trade.get("realized_pnl")

        action_str = "🟢매수" if action == "BUY" else "🔴매도"
        pnl_str = f"{format_number(pnl)}" if pnl else "-"

        print(f"  {date:<12} {action_str:>6} {code:>10} {format_number(price):>10} {qty:>6} {pnl_str:>12}")


def visualize_last_output(data: dict):
    """Show the last run output."""
    output = data.get("last_run_output", "")

    if not output:
        return

    print_subheader("마지막 실행 결과")
    print()
    print(output)


def create_ascii_chart(values: list, width: int = 50, height: int = 10) -> str:
    """Create a simple ASCII chart."""
    if not values or len(values) < 2:
        return "  (데이터 부족)"

    min_val = min(values)
    max_val = max(values)
    range_val = max_val - min_val if max_val > min_val else 1

    lines = []

    # Chart
    for h in range(height, 0, -1):
        threshold = min_val + (range_val * h / height)
        line = "  │"
        step = max(1, len(values) // width)

        for i in range(0, len(values), step):
            if values[i] >= threshold:
                line += "█"
            elif values[i] >= threshold - (range_val / height / 2):
                line += "▄"
            else:
                line += " "

        # Add value label on right
        if h == height:
            line += f" {format_number(max_val)}"
        elif h == 1:
            line += f" {format_number(min_val)}"

        lines.append(line)

    # X-axis
    lines.append("  └" + "─" * width)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Portfolio State Visualizer")
    parser.add_argument(
        "--file", "-f",
        default="portfolio_state.json",
        help="Path to portfolio_state.json"
    )
    parser.add_argument(
        "--output", "-o",
        action="store_true",
        help="Show last run output"
    )
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Skip fetching current prices (use entry prices only)"
    )
    args = parser.parse_args()

    # Check file exists
    if not Path(args.file).exists():
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    # Load and visualize
    data = load_portfolio(args.file)

    print("\n" + "█" * 70)
    print("█" + " " * 68 + "█")
    print("█" + "       📊 Daily Trading Wizard - Portfolio Visualizer".center(68) + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)

    # Get current prices for positions
    current_prices = None
    positions = data.get("positions", [])
    if positions:
        # Check if positions have stored current_price (from backtest)
        has_stored_prices = all(p.get("current_price") for p in positions)

        if has_stored_prices:
            # Use stored prices from backtest JSON
            current_prices = {p["stock_code"]: p["current_price"] for p in positions}
            end_date = data.get("end_date", "")
            print(f"\n  저장된 현재가 사용 ({end_date} 기준)")
        elif not args.no_fetch:
            # Fetch live prices from yfinance
            print("\n  현재가 조회 중...", end="", flush=True)
            stock_codes = [p.get("stock_code", "") for p in positions]
            current_prices = fetch_current_prices(stock_codes)
            print(f" {len(current_prices)}개 종목 완료 (실시간)")

    visualize_summary(data, current_prices)
    visualize_positions(data, current_prices)
    visualize_pending_orders(data)
    visualize_trade_history(data)

    if args.output:
        visualize_last_output(data)

    print("\n" + "=" * 70)
    print(f"  파일: {args.file}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
