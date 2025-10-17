"""
Performance metrics calculation.
Implements return, win rate, drawdown, and Sharpe ratio calculations.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

import numpy as np
import pandas as pd


@dataclass
class PerformanceReport:
    """
    Performance metrics from a backtest run.

    Attributes:
        total_return_pct: Total return percentage
        win_rate_pct: Percentage of winning trades
        max_drawdown_pct: Maximum drawdown percentage
        sharpe_ratio: Sharpe ratio
        cagr_pct: Compound annual growth rate
        num_trades: Total number of trades
        num_winning_trades: Number of winning trades
        num_losing_trades: Number of losing trades
        avg_win: Average winning trade P&L
        avg_loss: Average losing trade P&L
        win_loss_ratio: Ratio of avg win to avg loss
        profit_factor: Gross profit / gross loss
    """
    total_return_pct: Decimal
    win_rate_pct: Decimal
    max_drawdown_pct: Decimal
    sharpe_ratio: float
    cagr_pct: Decimal
    num_trades: int
    num_winning_trades: int
    num_losing_trades: int
    avg_win: Decimal
    avg_loss: Decimal
    win_loss_ratio: Optional[Decimal]
    profit_factor: Optional[Decimal]

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            'total_return_pct': float(self.total_return_pct),
            'win_rate_pct': float(self.win_rate_pct),
            'max_drawdown_pct': float(self.max_drawdown_pct),
            'sharpe_ratio': self.sharpe_ratio,
            'cagr_pct': float(self.cagr_pct),
            'num_trades': self.num_trades,
            'num_winning_trades': self.num_winning_trades,
            'num_losing_trades': self.num_losing_trades,
            'avg_win': float(self.avg_win),
            'avg_loss': float(self.avg_loss),
            'win_loss_ratio': float(self.win_loss_ratio) if self.win_loss_ratio else None,
            'profit_factor': float(self.profit_factor) if self.profit_factor else None
        }


def calculate_total_return(
    initial_capital: Decimal,
    final_value: Decimal
) -> Decimal:
    """Calculate total return percentage."""
    if initial_capital == 0:
        return Decimal('0')

    return ((final_value - initial_capital) / initial_capital) * 100


def calculate_win_rate(realized_pnls: List[Decimal]) -> Optional[Decimal]:
    """Calculate win rate percentage."""
    if not realized_pnls:
        return None

    winning_trades = sum(1 for pnl in realized_pnls if pnl > 0)
    return (Decimal(winning_trades) / Decimal(len(realized_pnls))) * 100


def calculate_max_drawdown(equity_curve: pd.Series) -> float:
    """Calculate maximum drawdown percentage."""
    # Calculate running maximum
    running_max = equity_curve.expanding().max()

    # Calculate drawdown at each point
    drawdown = (equity_curve - running_max) / running_max * 100

    # Return maximum drawdown (most negative)
    return float(drawdown.min())


def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252
) -> float:
    """
    Calculate Sharpe ratio.

    Args:
        returns: Series of returns
        risk_free_rate: Risk-free rate (daily)
        periods_per_year: Number of trading periods per year (252 for daily)

    Returns:
        Sharpe ratio (annualized)
    """
    if len(returns) == 0 or returns.std() == 0:
        return 0.0

    excess_returns = returns - risk_free_rate
    sharpe = (excess_returns.mean() / returns.std()) * np.sqrt(periods_per_year)

    return float(sharpe)


def calculate_cagr(
    initial_value: Decimal,
    final_value: Decimal,
    days: int
) -> Decimal:
    """
    Calculate Compound Annual Growth Rate.

    Args:
        initial_value: Starting value
        final_value: Ending value
        days: Number of days in period

    Returns:
        CAGR as percentage
    """
    if initial_value == 0 or days == 0:
        return Decimal('0')

    years = Decimal(days) / Decimal(365)
    cagr = (pow(float(final_value / initial_value), float(1 / years)) - 1) * 100

    return Decimal(str(cagr))


def calculate_avg_win_loss_ratio(realized_pnls: List[Decimal]) -> Optional[Decimal]:
    """Calculate average win to loss ratio."""
    wins = [pnl for pnl in realized_pnls if pnl > 0]
    losses = [abs(pnl) for pnl in realized_pnls if pnl < 0]

    if not wins or not losses:
        return None

    avg_win = sum(wins) / len(wins)
    avg_loss = sum(losses) / len(losses)

    return avg_win / avg_loss


def calculate_profit_factor(realized_pnls: List[Decimal]) -> Optional[Decimal]:
    """Calculate profit factor (gross profit / gross loss)."""
    gross_profit = sum(pnl for pnl in realized_pnls if pnl > 0)
    gross_loss = abs(sum(pnl for pnl in realized_pnls if pnl < 0))

    if gross_loss == 0:
        return None

    return gross_profit / gross_loss


def calculate_metrics_from_trades(
    trades: List,
    initial_capital: Decimal,
    backtest_start_date: Optional[datetime] = None,
    backtest_end_date: Optional[datetime] = None
) -> PerformanceReport:
    """
    Calculate all performance metrics from trade history.

    Args:
        trades: List of Trade objects
        initial_capital: Starting capital
        backtest_start_date: Backtest start date (for CAGR calculation)
        backtest_end_date: Backtest end date (for CAGR calculation)

    Returns:
        PerformanceReport with all metrics
    """
    # Extract realized P&Ls from SELL trades
    realized_pnls = [
        trade.realized_pnl
        for trade in trades
        if trade.realized_pnl is not None
    ]

    # Calculate basic metrics
    winning_trades = [pnl for pnl in realized_pnls if pnl > 0]
    losing_trades = [pnl for pnl in realized_pnls if pnl < 0]

    # Calculate final portfolio value
    if trades:
        # Get the final portfolio value from the last trade
        final_value = trades[-1].portfolio_value_after
    else:
        final_value = initial_capital

    # Total return
    total_return = calculate_total_return(initial_capital, final_value)

    # Win rate
    win_rate = calculate_win_rate(realized_pnls) or Decimal('0')

    # Build equity curve for drawdown and Sharpe
    equity_curve_data = []
    sharpe_ratio = 0.0
    max_drawdown = Decimal('0')

    if trades:
        # Create equity curve from trades
        for trade in trades:
            equity_curve_data.append({
                'date': trade.execution_timestamp,
                'portfolio_value': float(trade.portfolio_value_after)
            })

        equity_df = pd.DataFrame(equity_curve_data)
        equity_df = equity_df.set_index('date')
        equity_series = equity_df['portfolio_value']

        # Calculate max drawdown
        if len(equity_series) > 0:
            max_drawdown_float = calculate_max_drawdown(equity_series)
            max_drawdown = Decimal(str(max_drawdown_float))

        # Calculate Sharpe ratio from returns
        if len(equity_series) > 1:
            returns = equity_series.pct_change().dropna()
            sharpe_ratio = calculate_sharpe_ratio(returns)

    # Calculate CAGR
    cagr = Decimal('0')
    if trades:
        # Use backtest period if provided, otherwise fall back to trade dates
        if backtest_start_date and backtest_end_date:
            start_date = backtest_start_date
            end_date = backtest_end_date
        else:
            start_date = trades[0].execution_timestamp
            end_date = trades[-1].execution_timestamp

        days = (end_date - start_date).days
        if days > 0:
            cagr = calculate_cagr(initial_capital, final_value, days)

    return PerformanceReport(
        total_return_pct=total_return,
        win_rate_pct=win_rate,
        max_drawdown_pct=max_drawdown,
        sharpe_ratio=sharpe_ratio,
        cagr_pct=cagr,
        num_trades=len(trades),
        num_winning_trades=len(winning_trades),
        num_losing_trades=len(losing_trades),
        avg_win=sum(winning_trades) / len(winning_trades) if winning_trades else Decimal('0'),
        avg_loss=sum(losing_trades) / len(losing_trades) if losing_trades else Decimal('0'),
        win_loss_ratio=calculate_avg_win_loss_ratio(realized_pnls),
        profit_factor=calculate_profit_factor(realized_pnls)
    )


def analyze_filter_performance(trades: List) -> dict:
    """
    Analyze performance by filter pass/fail status (T072).

    Compares trades that passed different filter combinations.

    Args:
        trades: List of Trade objects with filter data

    Returns:
        Dictionary with filter performance analysis
    """
    from collections import defaultdict

    # Group buy trades by filter combinations
    filter_combinations = defaultdict(list)

    for trade in trades:
        if trade.action.value == "buy":
            # Create filter combo key
            filters = []
            if hasattr(trade, 'volume_pass') and trade.volume_pass:
                filters.append('volume')
            if hasattr(trade, 'rsi_pass') and trade.rsi_pass:
                filters.append('rsi')
            if hasattr(trade, 'macd_pass') and trade.macd_pass:
                filters.append('macd')

            combo = '+'.join(filters) if filters else 'baseline'
            filter_combinations[combo].append(trade)

    # Analyze each combination
    results = {}
    for combo, combo_trades in filter_combinations.items():
        # Find corresponding sell trades
        sell_trades = []
        for buy_trade in combo_trades:
            for trade in trades:
                if (trade.action.value == "sell" and
                    trade.stock_code == buy_trade.stock_code and
                    trade.execution_timestamp > buy_trade.execution_timestamp):
                    sell_trades.append(trade)
                    break

        # Calculate metrics for this combination
        pnls = [t.realized_pnl for t in sell_trades if t.realized_pnl is not None]
        if pnls:
            win_count = sum(1 for pnl in pnls if pnl > 0)
            results[combo] = {
                'count': len(combo_trades),
                'win_rate': (win_count / len(pnls)) * 100 if pnls else 0,
                'avg_pnl': float(sum(pnls) / len(pnls))
            }

    return results


def calculate_confidence_correlation(trades: List) -> Optional[float]:
    """
    Calculate correlation between confidence score and profit (T072: FR-014, SC-006).

    Args:
        trades: List of Trade objects with confidence_score and realized_pnl

    Returns:
        Pearson correlation coefficient, or None if insufficient data
    """
    # Extract buy-sell pairs with confidence scores
    buy_trades = {}
    for trade in trades:
        if trade.action.value == "buy" and hasattr(trade, 'confidence_score'):
            if trade.confidence_score is not None:
                buy_trades[trade.stock_code] = trade

    # Match with sell trades
    pairs = []
    for trade in trades:
        if trade.action.value == "sell" and trade.stock_code in buy_trades:
            buy = buy_trades[trade.stock_code]
            if trade.realized_pnl is not None:
                pairs.append({
                    'confidence': buy.confidence_score,
                    'pnl_pct': float(trade.realized_pnl / (buy.execution_price * buy.quantity) * 100)
                })
            # Remove to handle multiple round trips
            del buy_trades[trade.stock_code]

    if len(pairs) < 2:
        return None

    # Calculate Pearson correlation
    confidences = [p['confidence'] for p in pairs]
    pnl_pcts = [p['pnl_pct'] for p in pairs]

    correlation = np.corrcoef(confidences, pnl_pcts)[0, 1]

    return float(correlation) if not np.isnan(correlation) else None


def generate_filter_comparison_report(trades: List, initial_capital: Decimal) -> str:
    """
    Generate filter comparison report (T072).

    Args:
        trades: List of Trade objects
        initial_capital: Initial capital

    Returns:
        Formatted report string
    """
    lines = []
    lines.append("=" * 80)
    lines.append("📊 Filter Comparison Report")
    lines.append("=" * 80)

    # Filter performance analysis
    filter_perf = analyze_filter_performance(trades)

    if filter_perf:
        lines.append("\n필터 조합별 성능:")
        lines.append("-" * 80)
        for combo, metrics in sorted(filter_perf.items(), key=lambda x: x[1]['win_rate'], reverse=True):
            lines.append(f"\n{combo}:")
            lines.append(f"  거래 수:     {metrics['count']}")
            lines.append(f"  승률:       {metrics['win_rate']:.1f}%")
            lines.append(f"  평균 손익:   ₩{metrics['avg_pnl']:+,.0f}")

    # Confidence correlation
    correlation = calculate_confidence_correlation(trades)
    if correlation is not None:
        lines.append("\n" + "=" * 80)
        lines.append("📈 신뢰도 점수 vs 수익률 상관관계:")
        lines.append(f"  Pearson 상관계수: {correlation:+.3f}")

        if correlation > 0.3:
            lines.append("  ✅ 강한 양의 상관관계 - 신뢰도가 높을수록 수익 증가")
        elif correlation > 0:
            lines.append("  ✓ 약한 양의 상관관계 - 신뢰도와 수익이 약간 연관")
        elif correlation > -0.3:
            lines.append("  ⚠️  약한 음의 상관관계 - 거의 무관")
        else:
            lines.append("  ❌ 강한 음의 상관관계 - 신뢰도 시스템 재검토 필요")

    lines.append("\n" + "=" * 80)

    return "\n".join(lines)


def validate_backtest_results(
    trades: List,
    backtest_days: int,
    enabled_filters: dict,
    confidence_threshold: int,
    initial_capital: Decimal
) -> dict:
    """
    Validate backtest results and provide suggestions (T070, T071).
    
    Args:
        trades: List of Trade objects
        backtest_days: Number of days in backtest period
        enabled_filters: Dict with 'volume', 'rsi', 'macd' boolean flags
        confidence_threshold: Current confidence threshold
        initial_capital: Starting capital
        
    Returns:
        Dictionary with validation results and suggestions
    """
    validation = {
        'warnings': [],
        'suggestions': [],
        'max_achievable_score': 100,
        'current_threshold': confidence_threshold
    }
    
    # T070: Check for long periods without signals (30+ days with no trades)
    if len(trades) == 0:
        validation['warnings'].append(
            f"No trades generated during {backtest_days}-day backtest period"
        )
        
        # Calculate max achievable score with current enabled filters
        # Base score always included: 25
        max_score = 25
        filter_scores = {
            'volume': 25,
            'rsi': 20,
            'macd': 30
        }
        
        for filter_name, enabled in enabled_filters.items():
            if enabled and filter_name in filter_scores:
                max_score += filter_scores[filter_name]
        
        validation['max_achievable_score'] = max_score
        
        if confidence_threshold > max_score:
            validation['suggestions'].append(
                f"Confidence threshold ({confidence_threshold}) exceeds max achievable score ({max_score}). "
                f"Lower threshold to {max_score} or less."
            )
        elif max_score < 100:
            # Not all filters enabled
            disabled_filters = [name for name, enabled in enabled_filters.items() if not enabled]
            if disabled_filters:
                validation['suggestions'].append(
                    f"Consider enabling additional filters to increase max score: {', '.join(disabled_filters)}"
                )
        
        # Always suggest lowering threshold if too high
        if confidence_threshold >= 60:
            validation['suggestions'].append(
                f"Try lowering confidence threshold from {confidence_threshold} to 50 for more signals"
            )
    
    elif backtest_days >= 30:
        # Check for long gaps between trades
        trade_dates = [t.execution_timestamp for t in trades]
        trade_dates.sort()
        
        max_gap_days = 0
        for i in range(1, len(trade_dates)):
            gap = (trade_dates[i] - trade_dates[i-1]).days
            if gap > max_gap_days:
                max_gap_days = gap
        
        if max_gap_days >= 30:
            validation['warnings'].append(
                f"Maximum gap between trades: {max_gap_days} days (30+ days without signals)"
            )
            validation['suggestions'].append(
                "Consider lowering confidence threshold or adjusting filter parameters for more frequent signals"
            )
    
    # T071: Check for insufficient funds warnings (would require tracking rejected signals)
    # This would be better implemented in the backtest engine itself
    # For now, we can check if we have very few trades despite many signals
    # (This requires the engine to track rejected signals, which we'll add separately)
    
    return validation


def print_validation_report(validation: dict) -> None:
    """Print validation report with warnings and suggestions (T070)."""
    if not validation['warnings'] and not validation['suggestions']:
        return
    
    lines = []
    lines.append("\n" + "=" * 80)
    lines.append("⚠️  Backtest Validation Report")
    lines.append("=" * 80)
    
    if validation['warnings']:
        lines.append("\n경고:")
        for warning in validation['warnings']:
            lines.append(f"  ⚠️  {warning}")
    
    if validation['suggestions']:
        lines.append("\n권장사항:")
        for suggestion in validation['suggestions']:
            lines.append(f"  💡 {suggestion}")
    
    lines.append("\n설정 정보:")
    lines.append(f"  현재 임계값: {validation['current_threshold']}/100")
    lines.append(f"  최대 달성 가능 점수: {validation['max_achievable_score']}/100")
    
    lines.append("\n" + "=" * 80)
    
    print("\n".join(lines))
