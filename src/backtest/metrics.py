"""
Performance metrics calculation.
Implements return, win rate, drawdown, and Sharpe ratio calculations.
"""

import pandas as pd
from decimal import Decimal
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime
import numpy as np


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
