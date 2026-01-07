#!/usr/bin/env python
"""
Daily Trading Wizard - Generate next-day buy/sell recommendations.

Usage:
    python daily_wizard.py              # Run wizard (load existing or create new portfolio)
    python daily_wizard.py --init       # Initialize new portfolio with 1,000,000 KRW
    python daily_wizard.py --status     # Show current portfolio status only

Options:
    --init              Initialize new portfolio (1,000,000 KRW, starting 2026-01-05)
    --state-file PATH   Path to portfolio state JSON (default: portfolio_state.json)
    --no-time-check     Skip market hours check
    --status            Show current portfolio status only (no new recommendations)
"""

import argparse
import sys
from datetime import datetime, date
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.wizard.portfolio_manager import (
    PortfolioManager,
    WizardPortfolioState,
    PendingOrder,
)
from src.wizard.signal_scanner import SignalScanner, load_kospi_top100
from src.wizard.recommendation import (
    RecommendationEngine,
    format_recommendations_output,
    format_position_status,
)


# Configuration (optimized via time-period validation 2026-01-08)
INITIAL_CAPITAL = 1_000_000
START_DATE = "2026-01-05"
MAX_POSITIONS = 15
MAX_POSITION_PERCENT = 10.0
CONFIDENCE_THRESHOLD = 50
STOP_LOSS_PERCENT = 4.5
TAKE_PROFIT_PERCENT = 9.0


def generate_buy_reason_detail(rec) -> str:
    """Generate detailed explanation for BUY recommendation."""
    ind = rec.indicators

    # Check which filters passed
    volume_pass = ind.get("volume_ratio", 0) >= 1.5
    rsi_pass = 30 <= ind.get("rsi", 50) <= 70
    macd_pass = ind.get("macd_histogram", 0) > 0

    lines = []
    lines.append(f"[매수 추천] {rec.stock_code} ({rec.stock_name})")
    lines.append(f"")
    lines.append(f"1. 볼린저 밴드 상단 돌파 (Squeeze Breakout)")
    lines.append(
        f"   - 현재가 {rec.recommended_price:,.0f}원이 상단밴드 {ind.get('bb_upper', 0):,.0f}원을 돌파"
    )
    lines.append(f"   - 밴드폭: {ind.get('bb_width', 0):.2f}% (변동성 확대 중)")
    lines.append(f"")
    lines.append(f"2. 보조지표 분석")
    lines.append(
        f"   - RSI({ind.get('rsi', 0):.1f}): {'중립구간 ✓' if rsi_pass else '과매수/과매도 구간'}"
    )
    lines.append(
        f"   - MACD({ind.get('macd_histogram', 0):.2f}): {'상승추세 ✓' if macd_pass else '하락추세'}"
    )
    lines.append(
        f"   - 거래량({ind.get('volume_ratio', 0):.1f}x): {'평균 대비 급증 ✓' if volume_pass else '평균 수준'}"
    )
    lines.append(f"")
    lines.append(f"3. 신뢰도 점수: {rec.confidence_score}/100")
    lines.append(
        f"   - 기본(25) + {'Volume(25)' if volume_pass else 'Volume(0)'} + {'RSI(20)' if rsi_pass else 'RSI(0)'} + {'MACD(30)' if macd_pass else 'MACD(0)'}"
    )
    lines.append(f"")
    lines.append(f"4. 포지션 사이징")
    lines.append(f"   - 추천 수량: {rec.quantity}주")
    lines.append(
        f"   - 투자금액: {rec.total_cost:,.0f}원 (포트폴리오의 {rec.total_cost / INITIAL_CAPITAL * 100:.1f}%)"
    )

    return "\n".join(lines)


def generate_sell_reason_detail(rec) -> str:
    """Generate detailed explanation for SELL recommendation."""
    lines = []
    lines.append(f"[매도 추천] {rec.stock_code} ({rec.stock_name})")
    lines.append(f"")
    lines.append(f"1. 매도 사유: {rec.reason}")
    lines.append(f"")
    lines.append(f"2. 손익 현황")
    lines.append(f"   - 매수가: {rec.entry_price:,.0f}원")
    lines.append(f"   - 현재가: {rec.current_price:,.0f}원")
    lines.append(f"   - 수량: {rec.quantity}주")
    lines.append(f"   - 예상 손익: {rec.expected_pnl:+,.0f}원 ({rec.pnl_pct:+.1f}%)")
    lines.append(f"")

    if "stop_loss" in rec.reason:
        lines.append(f"3. 손절 기준")
        lines.append(f"   - 손절선 -{STOP_LOSS_PERCENT}% 도달")
        lines.append(f"   - 추가 하락 위험 방지를 위해 즉시 매도 권장")
    elif "lower_band" in rec.reason:
        lines.append(f"3. 기술적 매도 신호")
        lines.append(f"   - 가격이 볼린저 밴드 하단선 아래로 하락")
        lines.append(f"   - 추세 전환 가능성으로 청산 권장")

    return "\n".join(lines)


def check_market_hours() -> bool:
    """
    Check if it's after market close.
    Returns True if safe to run, False if market may still be open.
    """
    now = datetime.now()
    market_close_hour = 15  # 3:30 PM KST
    market_close_minute = 30

    # Weekend is always safe
    if now.weekday() >= 5:
        return True

    # After 3:30 PM is safe
    if now.hour > market_close_hour or (
        now.hour == market_close_hour and now.minute >= market_close_minute
    ):
        return True

    return False


def print_header():
    """Print wizard header."""
    print("=" * 70)
    print("Daily Trading Wizard")
    print("Bollinger Band Squeeze Strategy - KOSPI Top 100")
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


def show_status(pm: PortfolioManager):
    """Show current portfolio status only."""
    if not pm.exists():
        print("\nNo portfolio found. Run with --init to create a new portfolio.")
        return

    state = pm.load()
    scanner = SignalScanner()

    print("\nLoading current prices...")
    position_codes = [p.stock_code for p in state.positions]
    current_prices = scanner.get_current_prices(position_codes)

    # Calculate portfolio value
    summary = pm.calculate_portfolio_value(state, current_prices)

    print("\n" + "=" * 70)
    print("[PORTFOLIO STATUS]")
    print("=" * 70)
    print(f"  Start Date:         {state.start_date}")
    print(f"  Initial Capital:    {summary['initial_capital']:>12,.0f} KRW")
    print(f"  Cash Balance:       {summary['cash_balance']:>12,.0f} KRW")
    print(f"  Positions Value:    {summary['positions_value']:>12,.0f} KRW")
    print(f"  Total Value:        {summary['total_value']:>12,.0f} KRW")

    ret_pct = summary["total_return_pct"]
    ret_str = f"+{ret_pct:.2f}%" if ret_pct >= 0 else f"{ret_pct:.2f}%"
    print(f"  Total Return:       {ret_str:>13}")
    print(f"  Open Positions:     {summary['position_count']:>12} / {MAX_POSITIONS}")

    # Show positions
    print(format_position_status(state.positions, current_prices))

    # Show pending orders if any
    if state.pending_orders:
        print("\n[PENDING ORDERS]")
        print("-" * 70)
        for order in state.pending_orders:
            status = "EXECUTED" if order.executed else "PENDING"
            price_str = (
                f"{order.actual_price:,.0f}"
                if order.actual_price
                else f"{order.recommended_price:,.0f} (rec)"
            )
            print(
                f"  {order.action:<4} {order.stock_code} x {order.quantity} @ {price_str} [{status}]"
            )

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Daily Trading Wizard")
    parser.add_argument("--init", action="store_true", help="Initialize new portfolio")
    parser.add_argument(
        "--state-file",
        default="portfolio_state.json",
        help="Portfolio state file path",
    )
    parser.add_argument("--no-time-check", action="store_true", help="Skip market hours check")
    parser.add_argument("--status", action="store_true", help="Show current portfolio status only")
    args = parser.parse_args()

    print_header()

    # Initialize portfolio manager
    pm = PortfolioManager(args.state_file)

    # Status only mode
    if args.status:
        show_status(pm)
        return

    # Market hours check
    if not args.no_time_check and not check_market_hours():
        print("\nWARNING: Market may still be open (before 3:30 PM).")
        print("Run after market close for accurate signals.")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != "y":
            print("Aborted.")
            sys.exit(0)

    # Initialize new portfolio
    if args.init:
        if pm.exists():
            print(f"\nPortfolio already exists at: {args.state_file}")
            response = input("Overwrite? (y/N): ")
            if response.lower() != "y":
                print("Aborted.")
                sys.exit(0)

        state = WizardPortfolioState.initialize_new(
            initial_capital=INITIAL_CAPITAL, start_date=START_DATE
        )
        pm.save(state)
        print(f"\nInitialized new portfolio:")
        print(f"  Capital: {INITIAL_CAPITAL:,} KRW")
        print(f"  Start Date: {START_DATE}")
        print(f"  Saved to: {args.state_file}")
        print("\nRun again without --init to get recommendations.")
        return

    # Load or create portfolio
    state = pm.load_or_create(initial_capital=INITIAL_CAPITAL, start_date=START_DATE)

    # Process any pending orders marked as executed
    print("\n[1] Processing pending orders...")
    messages = pm.process_pending_orders(state)
    if messages:
        for msg in messages:
            print(f"    {msg}")
        pm.save(state)
    else:
        print("    No executed orders to process.")

    # Load stock universe
    print("\n[2] Loading KOSPI Top 100...")
    try:
        stock_codes = load_kospi_top100()
        print(f"    Loaded {len(stock_codes)} stocks")
    except FileNotFoundError as e:
        print(f"    ERROR: {e}")
        print("    Please ensure kospi_top100.txt exists.")
        sys.exit(1)

    # Initialize scanner
    scanner = SignalScanner(
        confidence_threshold=CONFIDENCE_THRESHOLD,
        stop_loss_percent=STOP_LOSS_PERCENT,
    )

    # Get existing position stock codes
    existing_positions = [p.stock_code for p in state.positions]

    # Scan for SELL signals (existing positions)
    print(f"\n[3] Scanning {len(state.positions)} positions for SELL signals...")
    sell_signals = scanner.scan_for_sell_signals(
        state.positions,
        progress_callback=lambda cur, tot, code: print(
            f"\r    Checking {cur}/{tot}: {code}    ", end=""
        ),
    )
    print(f"\r    Found {len(sell_signals)} SELL signals                    ")

    # Scan for BUY signals (new positions)
    candidates_count = len(stock_codes) - len(existing_positions)
    print(f"\n[4] Scanning {candidates_count} candidates for BUY signals...")
    buy_signals = scanner.scan_for_buy_signals(
        stock_codes,
        existing_positions,
        progress_callback=lambda cur, tot, code: print(
            f"\r    Scanning {cur}/{tot}: {code}    ", end=""
        ),
    )
    print(
        f"\r    Found {len(buy_signals)} BUY candidates (confidence >= {CONFIDENCE_THRESHOLD})    "
    )

    # Generate recommendations
    print("\n[5] Generating recommendations...")
    engine = RecommendationEngine(
        max_positions=MAX_POSITIONS,
        max_position_percent=MAX_POSITION_PERCENT,
        confidence_threshold=CONFIDENCE_THRESHOLD,
    )

    sell_recs = engine.generate_sell_recommendations(sell_signals, state.positions)
    buy_recs = engine.generate_buy_recommendations(
        buy_signals, state.cash_balance, len(state.positions)
    )

    # Get current prices for portfolio valuation
    all_position_codes = [p.stock_code for p in state.positions]
    all_position_codes.extend([s.stock_code for s in sell_signals])
    current_prices = {s.stock_code: s.current_price for s in sell_signals}
    for s in buy_signals:
        current_prices[s.stock_code] = s.current_price

    # Fill in missing prices
    missing_codes = [c for c in all_position_codes if c not in current_prices]
    if missing_codes:
        extra_prices = scanner.get_current_prices(missing_codes)
        current_prices.update(extra_prices)

    # Calculate portfolio summary
    summary = pm.calculate_portfolio_value(state, current_prices)
    summary["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary["max_positions"] = MAX_POSITIONS

    # Show current positions
    print(format_position_status(state.positions, current_prices))

    # Format and print recommendations
    output = format_recommendations_output(buy_recs, sell_recs, summary)
    print("\n" + output)

    # Update pending orders with detailed reasons
    state.pending_orders = []

    for rec in sell_recs:
        # Generate detailed sell reason
        reason_detail = generate_sell_reason_detail(rec)

        # Combine position info with technical indicators
        sell_indicators = {
            "entry_price": rec.entry_price,
            "current_price": rec.current_price,
            "pnl_pct": rec.pnl_pct,
            "expected_pnl": rec.expected_pnl,
        }
        sell_indicators.update(rec.indicators)

        state.pending_orders.append(
            PendingOrder(
                recommendation_date=date.today().isoformat(),
                stock_code=rec.stock_code,
                stock_name=rec.stock_name,
                action="SELL",
                recommended_price=rec.current_price,
                quantity=rec.quantity,
                reason_detail=reason_detail,
                indicators=sell_indicators,
            )
        )

    for rec in buy_recs:
        # Generate detailed buy reason
        reason_detail = generate_buy_reason_detail(rec)

        state.pending_orders.append(
            PendingOrder(
                recommendation_date=date.today().isoformat(),
                stock_code=rec.stock_code,
                stock_name=rec.stock_name,
                action="BUY",
                recommended_price=rec.recommended_price,
                quantity=rec.quantity,
                reason_detail=reason_detail,
                indicators=rec.indicators,
            )
        )

    # Save the output to state
    state.last_run_output = output

    # Save updated state
    pm.save(state)
    print(f"\nPortfolio state saved to: {args.state_file}")
    if state.pending_orders:
        print(f"Pending orders: {len(sell_recs)} SELL, {len(buy_recs)} BUY")


if __name__ == "__main__":
    main()
