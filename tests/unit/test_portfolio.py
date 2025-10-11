"""
Unit tests for Portfolio model (data-model.md Entity 1).
Tests cash_balance >= 0 validation, total_value computation, equity_curve ordering.

These tests MUST FAIL initially (TDD) until src/models/portfolio.py is implemented.
"""

import pytest
from decimal import Decimal
from datetime import datetime


def test_portfolio_initialization():
    """Test Portfolio can be created with valid parameters."""
    from src.models.portfolio import Portfolio

    portfolio = Portfolio(
        cash_balance=Decimal('10000000'),
        initial_capital=Decimal('10000000')
    )

    assert portfolio.cash_balance == Decimal('10000000')
    assert portfolio.initial_capital == Decimal('10000000')
    assert len(portfolio.positions) == 0
    assert len(portfolio.equity_curve) == 0


def test_portfolio_total_value_no_positions():
    """Test total_value equals cash when no positions held."""
    from src.models.portfolio import Portfolio

    portfolio = Portfolio(
        cash_balance=Decimal('10000000'),
        initial_capital=Decimal('10000000')
    )

    assert portfolio.total_value == Decimal('10000000')


def test_portfolio_cash_balance_cannot_be_negative():
    """Test Portfolio validates cash_balance >= 0 (constitutional requirement)."""
    from src.models.portfolio import Portfolio

    portfolio = Portfolio(
        cash_balance=Decimal('10000000'),
        initial_capital=Decimal('10000000')
    )

    # Attempt to set negative cash should raise error
    portfolio.cash_balance = Decimal('-1000')

    with pytest.raises(ValueError, match="negative"):
        portfolio.validate_cash_nonnegative()


def test_portfolio_record_snapshot():
    """Test recording portfolio state to equity curve."""
    from src.models.portfolio import Portfolio

    portfolio = Portfolio(
        cash_balance=Decimal('10000000'),
        initial_capital=Decimal('10000000')
    )

    timestamp1 = datetime(2024, 1, 1, 9, 0, 0)
    timestamp2 = datetime(2024, 1, 2, 9, 0, 0)

    portfolio.record_snapshot(timestamp1)
    portfolio.record_snapshot(timestamp2)

    assert len(portfolio.equity_curve) == 2
    assert portfolio.equity_curve[0][0] == timestamp1
    assert portfolio.equity_curve[0][1] == Decimal('10000000')
    assert portfolio.equity_curve[1][0] == timestamp2


def test_portfolio_equity_curve_chronological():
    """Test equity curve maintains chronological order."""
    from src.models.portfolio import Portfolio

    portfolio = Portfolio(
        cash_balance=Decimal('10000000'),
        initial_capital=Decimal('10000000')
    )

    t1 = datetime(2024, 1, 1, 9, 0, 0)
    t2 = datetime(2024, 1, 2, 9, 0, 0)
    t3 = datetime(2024, 1, 3, 9, 0, 0)

    portfolio.record_snapshot(t1)
    portfolio.record_snapshot(t2)
    portfolio.record_snapshot(t3)

    timestamps = [ts for ts, _ in portfolio.equity_curve]
    assert timestamps == sorted(timestamps)
