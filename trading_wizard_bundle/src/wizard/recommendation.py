"""
Recommendation generation and formatting for daily wizard.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

from src.wizard.portfolio_manager import WizardPosition
from src.wizard.signal_scanner import StockSignal


@dataclass
class BuyRecommendation:
    """BUY recommendation with position sizing."""

    stock_code: str
    stock_name: str
    recommended_price: float
    quantity: int
    total_cost: float
    confidence_score: int
    reason: str
    indicators: Dict[str, float]


@dataclass
class SellRecommendation:
    """SELL recommendation."""

    stock_code: str
    stock_name: str
    current_price: float
    quantity: int
    entry_price: float
    expected_pnl: float
    pnl_pct: float
    reason: str
    indicators: Dict[str, float]


class RecommendationEngine:
    """Generates buy/sell recommendations with position sizing and risk management."""

    def __init__(
        self,
        max_positions: int = 15,
        max_position_percent: float = 10.0,
        confidence_threshold: int = 60,
    ):
        """
        Initialize recommendation engine.

        Args:
            max_positions: Maximum number of positions allowed
            max_position_percent: Maximum percentage of capital per position
            confidence_threshold: Minimum confidence score for recommendations
        """
        self.max_positions = max_positions
        self.max_position_percent = max_position_percent
        self.confidence_threshold = confidence_threshold

    def generate_buy_recommendations(
        self,
        signals: List[StockSignal],
        cash_balance: float,
        current_position_count: int,
    ) -> List[BuyRecommendation]:
        """
        Generate BUY recommendations with position sizing.

        Args:
            signals: List of BUY signals from scanner
            cash_balance: Available cash
            current_position_count: Number of existing positions

        Returns:
            List of BuyRecommendation objects
        """
        recommendations = []
        available_slots = self.max_positions - current_position_count

        if available_slots <= 0:
            return []

        remaining_cash = cash_balance

        for signal in signals[:available_slots]:
            if signal.confidence_score < self.confidence_threshold:
                continue

            # Position sizing: max 10% of total capital per position
            max_allocation = cash_balance * (self.max_position_percent / 100)

            # Calculate max shares we can buy
            max_shares = int(max_allocation / signal.current_price)
            if max_shares < 1:
                continue

            total_cost = signal.current_price * max_shares

            # Check if we have enough cash
            if total_cost > remaining_cash:
                max_shares = int(remaining_cash / signal.current_price)
                total_cost = signal.current_price * max_shares

            if max_shares < 1:
                continue

            recommendations.append(
                BuyRecommendation(
                    stock_code=signal.stock_code,
                    stock_name=signal.stock_name,
                    recommended_price=signal.current_price,
                    quantity=max_shares,
                    total_cost=total_cost,
                    confidence_score=signal.confidence_score,
                    reason=signal.reason,
                    indicators=signal.indicators,
                )
            )

            # Update remaining cash for next recommendation
            remaining_cash -= total_cost

        return recommendations

    def generate_sell_recommendations(
        self,
        signals: List[StockSignal],
        positions: List[WizardPosition],
    ) -> List[SellRecommendation]:
        """
        Generate SELL recommendations.

        Args:
            signals: List of SELL signals from scanner
            positions: Current positions

        Returns:
            List of SellRecommendation objects
        """
        recommendations = []
        position_map = {p.stock_code: p for p in positions}

        for signal in signals:
            pos = position_map.get(signal.stock_code)
            if pos is None:
                continue

            pnl = (signal.current_price - pos.entry_price) * pos.quantity
            pnl_pct = ((signal.current_price - pos.entry_price) / pos.entry_price) * 100

            recommendations.append(
                SellRecommendation(
                    stock_code=signal.stock_code,
                    stock_name=signal.stock_name,
                    current_price=signal.current_price,
                    quantity=pos.quantity,
                    entry_price=pos.entry_price,
                    expected_pnl=pnl,
                    pnl_pct=pnl_pct,
                    reason=signal.reason,
                    indicators=signal.indicators,
                )
            )

        return recommendations


def format_recommendations_output(
    buy_recs: List[BuyRecommendation],
    sell_recs: List[SellRecommendation],
    portfolio_summary: Dict,
) -> str:
    """
    Format recommendations for console output.

    Args:
        buy_recs: List of BUY recommendations
        sell_recs: List of SELL recommendations
        portfolio_summary: Dict with portfolio metrics

    Returns:
        Formatted string for console output
    """
    lines = []
    lines.append("=" * 70)
    lines.append("Daily Trading Wizard - Recommendations")
    lines.append(f"Generated: {portfolio_summary.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}")
    lines.append("=" * 70)

    # Portfolio Summary
    lines.append("\n[PORTFOLIO SUMMARY]")
    lines.append(f"  Initial Capital:    {portfolio_summary['initial_capital']:>12,.0f} KRW")
    lines.append(f"  Cash Balance:       {portfolio_summary['cash_balance']:>12,.0f} KRW")
    lines.append(f"  Positions Value:    {portfolio_summary['positions_value']:>12,.0f} KRW")
    lines.append(f"  Total Value:        {portfolio_summary['total_value']:>12,.0f} KRW")

    # Return with color indicator
    ret_pct = portfolio_summary["total_return_pct"]
    ret_indicator = "+" if ret_pct >= 0 else ""
    lines.append(f"  Total Return:       {ret_indicator}{ret_pct:>11.2f}%")

    lines.append(
        f"  Open Positions:     {portfolio_summary['position_count']:>12d} / {portfolio_summary.get('max_positions', 15)}"
    )

    # Unrealized P&L
    if "unrealized_pnl" in portfolio_summary:
        upnl = portfolio_summary["unrealized_pnl"]
        upnl_indicator = "+" if upnl >= 0 else ""
        lines.append(f"  Unrealized PnL:     {upnl_indicator}{upnl:>11,.0f} KRW")

    # Realized P&L
    if "realized_pnl" in portfolio_summary:
        rpnl = portfolio_summary["realized_pnl"]
        rpnl_indicator = "+" if rpnl >= 0 else ""
        lines.append(f"  Realized PnL:       {rpnl_indicator}{rpnl:>11,.0f} KRW")

    # SELL Recommendations (Priority)
    lines.append("\n" + "-" * 70)
    if sell_recs:
        lines.append("[SELL RECOMMENDATIONS] - Execute First!")
        lines.append("-" * 70)
        for i, rec in enumerate(sell_recs, 1):
            pnl_indicator = "+" if rec.pnl_pct >= 0 else ""
            lines.append(f"  {i}. {rec.stock_code} ({rec.stock_name})")
            lines.append(f"     Reason: {rec.reason}")
            lines.append(
                f"     Entry: {rec.entry_price:,.0f} -> Current: {rec.current_price:,.0f}"
            )
            lines.append(
                f"     Quantity: {rec.quantity}, Expected PnL: {pnl_indicator}{rec.expected_pnl:,.0f} ({pnl_indicator}{rec.pnl_pct:.1f}%)"
            )
            lines.append("")
    else:
        lines.append("[SELL RECOMMENDATIONS]")
        lines.append("  No SELL signals.")

    # BUY Recommendations
    lines.append("\n" + "-" * 70)
    if buy_recs:
        lines.append("[BUY RECOMMENDATIONS]")
        lines.append("-" * 70)
        for i, rec in enumerate(buy_recs, 1):
            lines.append(f"  {i}. {rec.stock_code} ({rec.stock_name})")
            lines.append(f"     Confidence: {rec.confidence_score}/100")
            lines.append(f"     Price: {rec.recommended_price:,.0f} KRW")
            lines.append(
                f"     Quantity: {rec.quantity}, Total: {rec.total_cost:,.0f} KRW"
            )
            if rec.indicators:
                ind = rec.indicators
                lines.append(
                    f"     RSI: {ind.get('rsi', 0):.1f}, "
                    f"MACD: {ind.get('macd_histogram', 0):.2f}, "
                    f"Vol: {ind.get('volume_ratio', 0):.1f}x"
                )
            lines.append("")
    else:
        lines.append("[BUY RECOMMENDATIONS]")
        lines.append("  No BUY signals meeting criteria.")

    # Instructions
    lines.append("=" * 70)
    lines.append("To execute orders:")
    lines.append("1. Place orders tomorrow morning (market open)")
    lines.append("2. Edit portfolio_state.json with actual executed prices:")
    lines.append('   - Set "actual_price" to the executed price')
    lines.append('   - Set "executed" to true')
    lines.append("3. Run wizard again tomorrow after 3:30 PM")
    lines.append("=" * 70)

    return "\n".join(lines)


def format_position_status(
    positions: List[WizardPosition],
    current_prices: Dict[str, float],
) -> str:
    """
    Format current positions status.

    Args:
        positions: List of current positions
        current_prices: Dict of stock_code -> current_price

    Returns:
        Formatted string for console output
    """
    if not positions:
        return "\n[CURRENT POSITIONS]\n  No open positions."

    lines = []
    lines.append("\n[CURRENT POSITIONS]")
    lines.append("-" * 70)
    lines.append(
        f"  {'Code':<8} {'Entry':>10} {'Current':>10} {'Qty':>5} {'PnL':>12} {'Return':>8}"
    )
    lines.append("-" * 70)

    total_pnl = 0
    for pos in positions:
        current = current_prices.get(pos.stock_code, pos.entry_price)
        pnl = (current - pos.entry_price) * pos.quantity
        pnl_pct = ((current - pos.entry_price) / pos.entry_price) * 100
        total_pnl += pnl

        pnl_str = f"+{pnl:,.0f}" if pnl >= 0 else f"{pnl:,.0f}"
        pct_str = f"+{pnl_pct:.1f}%" if pnl_pct >= 0 else f"{pnl_pct:.1f}%"

        lines.append(
            f"  {pos.stock_code:<8} {pos.entry_price:>10,.0f} {current:>10,.0f} "
            f"{pos.quantity:>5} {pnl_str:>12} {pct_str:>8}"
        )

    lines.append("-" * 70)
    total_str = f"+{total_pnl:,.0f}" if total_pnl >= 0 else f"{total_pnl:,.0f}"
    lines.append(f"  {'TOTAL':<8} {'':<10} {'':<10} {'':<5} {total_str:>12}")

    return "\n".join(lines)
