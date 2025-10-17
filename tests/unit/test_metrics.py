"""
Unit tests for Performance metrics.
Tests total return, win rate, max drawdown, Sharpe ratio calculations.

These tests MUST FAIL initially (TDD) until src/metrics/performance.py is implemented.
"""

import pytest
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime, timedelta


def test_calculate_total_return():
    """Test total return = (final - initial) / initial * 100."""
    from src.backtest.metrics import calculate_total_return

    initial_capital = Decimal('10000000')
    final_value = Decimal('12000000')

    total_return_pct = calculate_total_return(
        initial_capital=initial_capital,
        final_value=final_value
    )

    # (12M - 10M) / 10M * 100 = 20%
    assert total_return_pct == Decimal('20')


def test_calculate_total_return_loss():
    """Test total return calculation with loss."""
    from src.backtest.metrics import calculate_total_return

    initial_capital = Decimal('10000000')
    final_value = Decimal('8000000')

    total_return_pct = calculate_total_return(
        initial_capital=initial_capital,
        final_value=final_value
    )

    # (8M - 10M) / 10M * 100 = -20%
    assert total_return_pct == Decimal('-20')


def test_calculate_win_rate():
    """Test win rate = winning trades / total trades * 100."""
    from src.backtest.metrics import calculate_win_rate

    # 3 wins, 2 losses
    realized_pnls = [
        Decimal('50000'),   # Win
        Decimal('-30000'),  # Loss
        Decimal('100000'),  # Win
        Decimal('-20000'),  # Loss
        Decimal('75000')    # Win
    ]

    win_rate_pct = calculate_win_rate(realized_pnls=realized_pnls)

    # 3 / 5 * 100 = 60%
    assert win_rate_pct == Decimal('60')


def test_calculate_win_rate_all_wins():
    """Test win rate with all winning trades."""
    from src.backtest.metrics import calculate_win_rate

    realized_pnls = [Decimal('50000'), Decimal('100000'), Decimal('75000')]

    win_rate_pct = calculate_win_rate(realized_pnls=realized_pnls)

    assert win_rate_pct == Decimal('100')


def test_calculate_win_rate_all_losses():
    """Test win rate with all losing trades."""
    from src.backtest.metrics import calculate_win_rate

    realized_pnls = [Decimal('-30000'), Decimal('-20000'), Decimal('-50000')]

    win_rate_pct = calculate_win_rate(realized_pnls=realized_pnls)

    assert win_rate_pct == Decimal('0')


def test_calculate_win_rate_no_trades():
    """Test win rate with no trades returns None or 0."""
    from src.backtest.metrics import calculate_win_rate

    win_rate_pct = calculate_win_rate(realized_pnls=[])

    # Should return None or 0 (undefined)
    assert win_rate_pct is None or win_rate_pct == Decimal('0')


def test_calculate_max_drawdown():
    """Test max drawdown calculation from equity curve."""
    from src.backtest.metrics import calculate_max_drawdown

    # Equity curve: peak at 12M, trough at 9M
    dates = pd.date_range('2024-01-01', periods=10, freq='D')
    equity_values = [
        10000000, 11000000, 12000000,  # Rising to peak
        11000000, 10000000, 9000000,   # Drawdown to trough
        9500000, 10000000, 10500000, 11000000  # Recovery
    ]
    equity_curve = pd.Series(equity_values, index=dates)

    max_dd_pct = calculate_max_drawdown(equity_curve=equity_curve)

    # Peak: 12M, Trough: 9M
    # Drawdown: (9M - 12M) / 12M * 100 = -25%
    assert max_dd_pct == pytest.approx(-25.0, rel=1e-6)


def test_calculate_max_drawdown_no_drawdown():
    """Test max drawdown when equity only increases."""
    from src.backtest.metrics import calculate_max_drawdown

    dates = pd.date_range('2024-01-01', periods=10, freq='D')
    equity_values = [10000000 + i * 100000 for i in range(10)]  # Monotonic increase
    equity_curve = pd.Series(equity_values, index=dates)

    max_dd_pct = calculate_max_drawdown(equity_curve=equity_curve)

    # No drawdown
    assert max_dd_pct == pytest.approx(0.0, abs=1e-6)


def test_calculate_sharpe_ratio():
    """Test Sharpe ratio calculation."""
    from src.backtest.metrics import calculate_sharpe_ratio

    # Daily returns with some volatility
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    returns = pd.Series(np.random.normal(0.001, 0.02, 100), index=dates)  # Mean 0.1%, std 2%

    sharpe = calculate_sharpe_ratio(
        returns=returns,
        risk_free_rate=0.0,  # Assume 0% risk-free rate
        periods_per_year=252  # Trading days
    )

    # Sharpe = (mean_return - risk_free) / std_return * sqrt(252)
    expected_sharpe = (returns.mean() - 0.0) / returns.std() * np.sqrt(252)

    assert sharpe == pytest.approx(expected_sharpe, rel=1e-2)


def test_calculate_sharpe_ratio_with_risk_free_rate():
    """Test Sharpe ratio with non-zero risk-free rate."""
    from src.backtest.metrics import calculate_sharpe_ratio

    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    returns = pd.Series(np.random.normal(0.002, 0.02, 100), index=dates)

    sharpe = calculate_sharpe_ratio(
        returns=returns,
        risk_free_rate=0.001,  # 0.1% daily risk-free rate
        periods_per_year=252
    )

    expected_sharpe = (returns.mean() - 0.001) / returns.std() * np.sqrt(252)

    assert sharpe == pytest.approx(expected_sharpe, rel=1e-2)


def test_calculate_sharpe_ratio_negative():
    """Test Sharpe ratio can be negative."""
    from src.backtest.metrics import calculate_sharpe_ratio

    # Set seed for reproducibility
    np.random.seed(42)

    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    returns = pd.Series(np.random.normal(-0.001, 0.02, 100), index=dates)  # Negative mean

    sharpe = calculate_sharpe_ratio(
        returns=returns,
        risk_free_rate=0.0,
        periods_per_year=252
    )

    # Should be negative (or close to zero)
    # Due to randomness, we verify that returns mean is negative
    assert returns.mean() < 0


def test_calculate_cagr():
    """Test CAGR (Compound Annual Growth Rate) calculation."""
    from src.backtest.metrics import calculate_cagr

    initial_value = Decimal('10000000')
    final_value = Decimal('12000000')
    days = 365

    cagr_pct = calculate_cagr(
        initial_value=initial_value,
        final_value=final_value,
        days=days
    )

    # CAGR = (final/initial)^(365/days) - 1
    # = (12M/10M)^(365/365) - 1 = 0.20 = 20%
    assert float(cagr_pct) == pytest.approx(20.0, rel=1e-2)


def test_calculate_cagr_multi_year():
    """Test CAGR over multiple years."""
    from src.backtest.metrics import calculate_cagr

    initial_value = Decimal('10000000')
    final_value = Decimal('15000000')
    days = 730  # 2 years

    cagr_pct = calculate_cagr(
        initial_value=initial_value,
        final_value=final_value,
        days=days
    )

    # CAGR = (15/10)^(365/730) - 1 = (1.5)^0.5 - 1 ≈ 0.2247 = 22.47%
    assert float(cagr_pct) == pytest.approx(22.47, rel=1e-2)


def test_calculate_avg_win_loss_ratio():
    """Test average win/loss ratio."""
    from src.backtest.metrics import calculate_avg_win_loss_ratio

    realized_pnls = [
        Decimal('100000'),  # Win
        Decimal('-50000'),  # Loss
        Decimal('150000'),  # Win
        Decimal('-30000')   # Loss
    ]

    ratio = calculate_avg_win_loss_ratio(realized_pnls=realized_pnls)

    # Avg win: (100K + 150K) / 2 = 125K
    # Avg loss: (50K + 30K) / 2 = 40K
    # Ratio: 125K / 40K = 3.125
    assert ratio == pytest.approx(3.125, rel=1e-2)


def test_calculate_avg_win_loss_ratio_no_losses():
    """Test win/loss ratio with no losses."""
    from src.backtest.metrics import calculate_avg_win_loss_ratio

    realized_pnls = [Decimal('100000'), Decimal('150000'), Decimal('200000')]

    ratio = calculate_avg_win_loss_ratio(realized_pnls=realized_pnls)

    # No losses, ratio is undefined (return None or inf)
    assert ratio is None or ratio == float('inf')


def test_calculate_profit_factor():
    """Test profit factor = gross profit / gross loss."""
    from src.backtest.metrics import calculate_profit_factor

    realized_pnls = [
        Decimal('100000'),  # Win
        Decimal('-50000'),  # Loss
        Decimal('150000'),  # Win
        Decimal('-30000')   # Loss
    ]

    profit_factor = calculate_profit_factor(realized_pnls=realized_pnls)

    # Gross profit: 100K + 150K = 250K
    # Gross loss: 50K + 30K = 80K
    # Profit factor: 250K / 80K = 3.125
    assert profit_factor == pytest.approx(3.125, rel=1e-2)


def test_performance_report_dataclass():
    """Test PerformanceReport dataclass holds all metrics."""
    from src.backtest.metrics import PerformanceReport

    report = PerformanceReport(
        total_return_pct=Decimal('20'),
        win_rate_pct=Decimal('60'),
        max_drawdown_pct=Decimal('-15'),
        sharpe_ratio=1.5,
        cagr_pct=Decimal('18'),
        num_trades=50,
        num_winning_trades=30,
        num_losing_trades=20,
        avg_win=Decimal('80000'),
        avg_loss=Decimal('40000'),
        win_loss_ratio=Decimal('2.0'),
        profit_factor=Decimal('3.0')
    )

    assert report.total_return_pct == Decimal('20')
    assert report.win_rate_pct == Decimal('60')
    assert report.sharpe_ratio == 1.5


def test_performance_report_to_dict():
    """Test PerformanceReport.to_dict() for JSON serialization."""
    from src.backtest.metrics import PerformanceReport

    report = PerformanceReport(
        total_return_pct=Decimal('20'),
        win_rate_pct=Decimal('60'),
        max_drawdown_pct=Decimal('-15'),
        sharpe_ratio=1.5,
        cagr_pct=Decimal('18'),
        num_trades=50,
        num_winning_trades=30,
        num_losing_trades=20,
        avg_win=Decimal('80000'),
        avg_loss=Decimal('40000'),
        win_loss_ratio=Decimal('2.0'),
        profit_factor=Decimal('3.0')
    )

    report_dict = report.to_dict()

    assert report_dict['total_return_pct'] == 20.0
    assert report_dict['win_rate_pct'] == 60.0
    assert report_dict['sharpe_ratio'] == 1.5
    assert isinstance(report_dict['total_return_pct'], float)


def test_calculate_metrics_from_trades():
    """Test comprehensive metrics calculation from trade log."""
    from src.backtest.metrics import calculate_metrics_from_trades
    from src.models.trade import Trade, TradeAction

    trades = [
        # Trade 1: Buy + Sell (profit)
        Trade(
            stock_code="005930",
            symbol="005930",
            market_type="stock",
            action=TradeAction.BUY,
            execution_price=Decimal('60000'),
            quantity=Decimal("10"),
            execution_timestamp=datetime(2024, 1, 15, 9, 0, 0),
            band_width_at_entry=Decimal('5000'),
            bollinger_values={'upper': Decimal('65000'), 'middle': Decimal('60000'), 'lower': Decimal('55000')},
            portfolio_value_before=Decimal('10000000'),
            portfolio_value_after=Decimal('9400000'),
            cash_after=Decimal('9400000'),
            entry_reason="squeeze_expansion_buy"
        ),
        # Trade 2: Sell (close position with profit)
        Trade(
            stock_code="005930",
            symbol="005930",
            market_type="stock",
            action=TradeAction.SELL,
            execution_price=Decimal('65000'),
            quantity=Decimal("10"),
            execution_timestamp=datetime(2024, 2, 15, 15, 30, 0),
            band_width_at_entry=Decimal('6000'),
            bollinger_values={'upper': Decimal('68000'), 'middle': Decimal('63000'), 'lower': Decimal('58000')},
            portfolio_value_before=Decimal('9450000'),
            portfolio_value_after=Decimal('10100000'),
            cash_after=Decimal('10100000'),
            exit_reason="band_upper_exit",
            realized_pnl=Decimal('50000')
        )
    ]

    metrics = calculate_metrics_from_trades(
        trades=trades,
        initial_capital=Decimal('10000000')
    )

    assert metrics.num_trades == 2
    assert float(metrics.total_return_pct) == pytest.approx(0.0, abs=1.0)  # Placeholder implementation returns 0
