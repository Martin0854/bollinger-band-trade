"""
Unit tests for Risk controls.
Tests stop-loss (5% default), position sizing (max 30% per stock), max positions (5).

These tests MUST FAIL initially (TDD) until src/risk/controls.py is implemented.
"""

import pytest
from decimal import Decimal
from datetime import datetime
import pytz


def test_stop_loss_triggered_at_threshold():
    """Test stop-loss triggers when position loses 5% (FR-033)."""
    from src.risk.controls import check_stop_loss

    purchase_price = Decimal('60000')
    current_price = Decimal('57000')  # 5% loss
    stop_loss_pct = Decimal('5')

    should_exit = check_stop_loss(
        purchase_price=purchase_price,
        current_price=current_price,
        stop_loss_percent=stop_loss_pct
    )

    assert should_exit is True


def test_stop_loss_not_triggered_below_threshold():
    """Test stop-loss does NOT trigger when loss < threshold."""
    from src.risk.controls import check_stop_loss

    purchase_price = Decimal('60000')
    current_price = Decimal('58000')  # 3.33% loss (below 5%)
    stop_loss_pct = Decimal('5')

    should_exit = check_stop_loss(
        purchase_price=purchase_price,
        current_price=current_price,
        stop_loss_percent=stop_loss_pct
    )

    assert should_exit is False


def test_stop_loss_not_triggered_on_profit():
    """Test stop-loss does NOT trigger when position is profitable."""
    from src.risk.controls import check_stop_loss

    purchase_price = Decimal('60000')
    current_price = Decimal('65000')  # Profit
    stop_loss_pct = Decimal('5')

    should_exit = check_stop_loss(
        purchase_price=purchase_price,
        current_price=current_price,
        stop_loss_percent=stop_loss_pct
    )

    assert should_exit is False


def test_position_sizing_max_30_percent():
    """Test position sizing limits single stock to 30% of portfolio (FR-030)."""
    from src.risk.controls import calculate_position_size

    portfolio_value = Decimal('10000000')  # 10M KRW
    stock_price = Decimal('60000')
    max_position_pct = Decimal('30')

    quantity = calculate_position_size(
        portfolio_value=portfolio_value,
        stock_price=stock_price,
        max_position_percent=max_position_pct
    )

    # Max allocation: 10M * 30% = 3M KRW
    # Shares: 3M / 60000 = 50 shares
    assert quantity == 50

    # Verify cost is <= 30% of portfolio
    cost = quantity * stock_price
    assert cost <= portfolio_value * (max_position_pct / 100)


def test_position_sizing_insufficient_cash():
    """Test position sizing when cash < max position size."""
    from src.risk.controls import calculate_position_size

    portfolio_value = Decimal('1000000')  # Only 1M KRW
    stock_price = Decimal('60000')
    max_position_pct = Decimal('30')

    quantity = calculate_position_size(
        portfolio_value=portfolio_value,
        stock_price=stock_price,
        max_position_percent=max_position_pct
    )

    # Max allocation: 1M * 30% = 300K KRW
    # Shares: 300K / 60000 = 5 shares
    assert quantity == 5


def test_position_sizing_high_price_stock():
    """Test position sizing with high-priced stock."""
    from src.risk.controls import calculate_position_size

    portfolio_value = Decimal('10000000')
    stock_price = Decimal('500000')  # High price (e.g., Samsung Electronics)
    max_position_pct = Decimal('30')

    quantity = calculate_position_size(
        portfolio_value=portfolio_value,
        stock_price=stock_price,
        max_position_percent=max_position_pct
    )

    # Max allocation: 10M * 30% = 3M KRW
    # Shares: 3M / 500000 = 6 shares
    assert quantity == 6


def test_max_positions_limit():
    """Test portfolio cannot hold more than 5 positions (FR-031)."""
    from src.risk.controls import can_open_new_position

    current_positions = 5
    max_positions = 5

    can_open = can_open_new_position(
        current_position_count=current_positions,
        max_positions=max_positions
    )

    assert can_open is False


def test_can_open_position_below_limit():
    """Test portfolio can open new position when below limit."""
    from src.risk.controls import can_open_new_position

    current_positions = 3
    max_positions = 5

    can_open = can_open_new_position(
        current_position_count=current_positions,
        max_positions=max_positions
    )

    assert can_open is True


def test_validate_sufficient_cash():
    """Test validation of sufficient cash for trade."""
    from src.risk.controls import validate_sufficient_cash

    cash_balance = Decimal('5000000')
    required_cash = Decimal('3000000')

    # Should not raise exception
    validate_sufficient_cash(
        cash_balance=cash_balance,
        required_cash=required_cash
    )


def test_validate_insufficient_cash_raises():
    """Test validation raises when insufficient cash."""
    from src.risk.controls import validate_sufficient_cash

    cash_balance = Decimal('2000000')
    required_cash = Decimal('3000000')

    with pytest.raises(ValueError, match="Insufficient cash"):
        validate_sufficient_cash(
            cash_balance=cash_balance,
            required_cash=required_cash
        )


def test_calculate_trade_value():
    """Test trade value calculation = quantity * price."""
    from src.risk.controls import calculate_trade_value

    quantity = 10
    price = Decimal('60000')

    trade_value = calculate_trade_value(
        quantity=quantity,
        price=price
    )

    assert trade_value == Decimal('600000')


def test_position_sizing_returns_zero_when_cannot_afford():
    """Test position sizing returns 0 when stock price > max allocation."""
    from src.risk.controls import calculate_position_size

    portfolio_value = Decimal('1000000')  # 1M KRW
    stock_price = Decimal('500000')       # Stock costs 500K
    max_position_pct = Decimal('30')      # Max: 300K (< 500K)

    quantity = calculate_position_size(
        portfolio_value=portfolio_value,
        stock_price=stock_price,
        max_position_percent=max_position_pct
    )

    # Cannot afford even 1 share
    assert quantity == 0


def test_stop_loss_validation_percent_positive():
    """Test stop-loss validates percent > 0."""
    from src.risk.controls import check_stop_loss

    with pytest.raises(ValueError, match="positive"):
        check_stop_loss(
            purchase_price=Decimal('60000'),
            current_price=Decimal('57000'),
            stop_loss_percent=Decimal('0')  # Invalid
        )


def test_position_sizing_validation_percent_range():
    """Test position sizing validates percent in (0, 100]."""
    from src.risk.controls import calculate_position_size

    with pytest.raises(ValueError, match="percent"):
        calculate_position_size(
            portfolio_value=Decimal('10000000'),
            stock_price=Decimal('60000'),
            max_position_percent=Decimal('150')  # Invalid: > 100
        )


def test_risk_limits_configuration():
    """Test RiskLimits dataclass holds all risk parameters."""
    from src.risk.controls import RiskLimits

    limits = RiskLimits(
        stop_loss_percent=Decimal('5'),
        max_position_percent=Decimal('30'),
        max_positions=5
    )

    assert limits.stop_loss_percent == Decimal('5')
    assert limits.max_position_percent == Decimal('30')
    assert limits.max_positions == 5


def test_risk_limits_defaults():
    """Test RiskLimits has correct default values."""
    from src.risk.controls import RiskLimits

    limits = RiskLimits()

    # Defaults per spec
    assert limits.stop_loss_percent == Decimal('5')
    assert limits.max_position_percent == Decimal('30')
    assert limits.max_positions == 5


def test_check_all_positions_for_stop_loss():
    """Test checking multiple positions for stop-loss triggers."""
    from src.risk.controls import check_positions_for_stop_loss
    from src.models.portfolio import Position

    positions = [
        Position(
            stock_code="005930",
            quantity=10,
            purchase_price=Decimal('60000'),
            purchase_date=datetime(2024, 1, 15),
            entry_reason="squeeze_expansion_buy"
        ),
        Position(
            stock_code="035720",
            quantity=5,
            purchase_price=Decimal('100000'),
            purchase_date=datetime(2024, 1, 16),
            entry_reason="squeeze_expansion_buy"
        )
    ]

    # Set current prices: first position loses 5%, second is profitable
    positions[0].current_price = Decimal('57000')  # 5% loss
    positions[1].current_price = Decimal('105000')  # Profit

    triggered = check_positions_for_stop_loss(
        positions=positions,
        stop_loss_percent=Decimal('5')
    )

    # Should return list with only first position (005930)
    assert len(triggered) == 1
    assert triggered[0].stock_code == "005930"


def test_portfolio_position_concentration():
    """Test calculation of portfolio position concentration."""
    from src.risk.controls import calculate_portfolio_concentration
    from src.models.portfolio import Position

    positions = [
        Position(
            stock_code="005930",
            quantity=10,
            purchase_price=Decimal('60000'),
            purchase_date=datetime(2024, 1, 15),
            entry_reason="squeeze_expansion_buy"
        ),
        Position(
            stock_code="035720",
            quantity=5,
            purchase_price=Decimal('40000'),
            purchase_date=datetime(2024, 1, 16),
            entry_reason="squeeze_expansion_buy"
        )
    ]

    # Set current prices
    positions[0].current_price = Decimal('60000')  # 600K value
    positions[1].current_price = Decimal('40000')  # 200K value

    total_portfolio_value = Decimal('10000000')

    concentration = calculate_portfolio_concentration(
        positions=positions,
        total_portfolio_value=total_portfolio_value
    )

    # Position 1: 600K / 10M = 6%
    # Position 2: 200K / 10M = 2%
    assert concentration["005930"] == pytest.approx(6.0, rel=1e-2)
    assert concentration["035720"] == pytest.approx(2.0, rel=1e-2)


# ========================================================================
# T059: RiskManager Dynamic Stop-Loss Tests (User Story 5)
# ========================================================================

def test_risk_manager_calculate_stop_loss_atr_enabled():
    """
    T059: Test ATR enabled → uses dynamic stop-loss.

    When ATR is enabled and ATR value is provided, RiskManager
    should calculate stop-loss based on ATR instead of fixed percentage.
    """
    pytest.skip("ATR not yet implemented - will implement in T061-T066")

    # from src.risk.controls import RiskManager
    # from src.indicators.momentum import ATRIndicator

    # # Given: RiskManager with ATR enabled
    # atr_indicator = ATRIndicator(period=14, multiplier=2.0)
    # risk_manager = RiskManager(
    #     stop_loss_percent=Decimal('5.0'),
    #     atr_indicator=atr_indicator
    # )

    # entry_price = Decimal('60000')
    # atr_value = Decimal('1000')  # ATR = 1000

    # # When: Calculate stop-loss with ATR
    # stop_loss = risk_manager.calculate_stop_loss(
    #     entry_price=entry_price,
    #     fixed_percent=Decimal('5.0'),
    #     atr_value=atr_value
    # )

    # # Then: Should use ATR calculation: 60000 - (1000 * 2.0) = 58000
    # assert stop_loss == Decimal('58000')
    # # NOT fixed 5%: 60000 * 0.95 = 57000


def test_risk_manager_calculate_stop_loss_atr_disabled():
    """
    T059: Test ATR disabled → uses fixed percentage.

    When ATR is disabled or not configured, RiskManager should
    fall back to traditional fixed percentage stop-loss.
    """
    pytest.skip("ATR not yet implemented - will implement in T061-T066")

    # from src.risk.controls import RiskManager

    # # Given: RiskManager without ATR (disabled)
    # risk_manager = RiskManager(
    #     stop_loss_percent=Decimal('5.0'),
    #     atr_indicator=None  # No ATR
    # )

    # entry_price = Decimal('60000')

    # # When: Calculate stop-loss without ATR
    # stop_loss = risk_manager.calculate_stop_loss(
    #     entry_price=entry_price,
    #     fixed_percent=Decimal('5.0'),
    #     atr_value=None  # No ATR value
    # )

    # # Then: Should use fixed 5%: 60000 * 0.95 = 57000
    # assert stop_loss == Decimal('57000')


def test_risk_manager_calculate_stop_loss_atr_none_falls_back():
    """
    T059: Test ATR=None → falls back to fixed percentage.

    Even if ATR indicator is configured, if ATR value is None
    (e.g., insufficient data), should fall back to fixed percentage.
    """
    pytest.skip("ATR not yet implemented - will implement in T061-T066")

    # from src.risk.controls import RiskManager
    # from src.indicators.momentum import ATRIndicator

    # # Given: RiskManager with ATR, but ATR value is None
    # atr_indicator = ATRIndicator(period=14, multiplier=2.0)
    # risk_manager = RiskManager(
    #     stop_loss_percent=Decimal('5.0'),
    #     atr_indicator=atr_indicator
    # )

    # entry_price = Decimal('60000')

    # # When: Calculate stop-loss with ATR=None (insufficient data)
    # stop_loss = risk_manager.calculate_stop_loss(
    #     entry_price=entry_price,
    #     fixed_percent=Decimal('5.0'),
    #     atr_value=None  # ATR calculation failed
    # )

    # # Then: Should fall back to fixed 5%
    # assert stop_loss == Decimal('57000')
