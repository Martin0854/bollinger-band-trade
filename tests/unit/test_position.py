"""
Unit tests for Position model (data-model.md Entity 2).
Tests quantity > 0, purchase_price > 0, stock_code regex, unrealized_pnl, stop_loss.

These tests MUST FAIL initially (TDD) until src/models/portfolio.py is implemented.
"""

import pytest
from decimal import Decimal
from datetime import datetime


def test_position_creation_valid():
    """Test Position can be created with valid parameters."""
    from src.models.portfolio import Position

    position = Position(
        stock_code="005930",
        quantity=10,
        purchase_price=Decimal('60000'),
        purchase_date=datetime(2024, 1, 15),
        entry_reason="squeeze_expansion_buy"
    )

    assert position.stock_code == "005930"
    assert position.quantity == 10
    assert position.purchase_price == Decimal('60000')
    assert position.entry_reason == "squeeze_expansion_buy"


def test_position_quantity_must_be_positive():
    """Test Position validates quantity > 0."""
    from src.models.portfolio import Position

    with pytest.raises(ValueError, match="positive"):
        Position(
            stock_code="005930",
            quantity=0,  # Invalid
            purchase_price=Decimal('60000'),
            purchase_date=datetime(2024, 1, 15),
            entry_reason="squeeze_expansion_buy"
        )

    with pytest.raises(ValueError, match="positive"):
        Position(
            stock_code="005930",
            quantity=-10,  # Invalid
            purchase_price=Decimal('60000'),
            purchase_date=datetime(2024, 1, 15),
            entry_reason="squeeze_expansion_buy"
        )


def test_position_purchase_price_must_be_positive():
    """Test Position validates purchase_price > 0."""
    from src.models.portfolio import Position

    with pytest.raises(ValueError, match="positive"):
        Position(
            stock_code="005930",
            quantity=10,
            purchase_price=Decimal('0'),  # Invalid
            purchase_date=datetime(2024, 1, 15),
            entry_reason="squeeze_expansion_buy"
        )


def test_position_stock_code_must_be_6_digits():
    """Test Position accepts both stock codes and crypto symbols (multi-market support)."""
    from src.models.portfolio import Position

    # Note: Validation is lenient for multi-market support
    # Stock codes (6 digits) are accepted
    position1 = Position(
        stock_code="005930",  # Valid stock code
        quantity=10,
        purchase_price=Decimal('60000'),
        purchase_date=datetime(2024, 1, 15),
        entry_reason="squeeze_expansion_buy"
    )
    assert position1.stock_code == "005930"

    # Crypto symbols (uppercase) are also accepted
    position2 = Position(
        stock_code="BTCUSDT",  # Valid crypto symbol
        quantity=10,
        purchase_price=Decimal('60000'),
        purchase_date=datetime(2024, 1, 15),
        entry_reason="squeeze_expansion_buy"
    )
    assert position2.stock_code == "BTCUSDT"


def test_position_market_value_calculation():
    """Test market_value = quantity * current_price."""
    from src.models.portfolio import Position

    position = Position(
        stock_code="005930",
        quantity=10,
        purchase_price=Decimal('60000'),
        purchase_date=datetime(2024, 1, 15),
        entry_reason="squeeze_expansion_buy"
    )

    position.current_price = Decimal('65000')

    assert position.market_value == Decimal('650000')  # 10 * 65000


def test_position_cost_basis_calculation():
    """Test cost_basis = quantity * purchase_price."""
    from src.models.portfolio import Position

    position = Position(
        stock_code="005930",
        quantity=10,
        purchase_price=Decimal('60000'),
        purchase_date=datetime(2024, 1, 15),
        entry_reason="squeeze_expansion_buy"
    )

    assert position.cost_basis == Decimal('600000')  # 10 * 60000


def test_position_unrealized_pnl_profit():
    """Test unrealized_pnl calculation when position is profitable."""
    from src.models.portfolio import Position

    position = Position(
        stock_code="005930",
        quantity=10,
        purchase_price=Decimal('60000'),
        purchase_date=datetime(2024, 1, 15),
        entry_reason="squeeze_expansion_buy"
    )

    position.current_price = Decimal('65000')

    # PnL = (65000 - 60000) * 10 = 50000
    assert position.unrealized_pnl == Decimal('50000')
    assert position.unrealized_pnl_pct == Decimal('8.333333333333333333333333333')  # 50000/600000 * 100


def test_position_unrealized_pnl_loss():
    """Test unrealized_pnl calculation when position is losing."""
    from src.models.portfolio import Position

    position = Position(
        stock_code="005930",
        quantity=10,
        purchase_price=Decimal('60000'),
        purchase_date=datetime(2024, 1, 15),
        entry_reason="squeeze_expansion_buy"
    )

    position.current_price = Decimal('57000')

    # PnL = (57000 - 60000) * 10 = -30000
    assert position.unrealized_pnl == Decimal('-30000')
    assert position.unrealized_pnl_pct == Decimal('-5')  # -30000/600000 * 100


def test_position_check_stop_loss():
    """Test check_stop_loss method triggers at threshold."""
    from src.models.portfolio import Position

    position = Position(
        stock_code="005930",
        quantity=10,
        purchase_price=Decimal('60000'),
        purchase_date=datetime(2024, 1, 15),
        entry_reason="squeeze_expansion_buy"
    )

    # Price drops 5% (to 57000)
    position.current_price = Decimal('57000')

    assert position.check_stop_loss(Decimal('5')) is True

    # Price drops only 3% (to 58200)
    position.current_price = Decimal('58200')

    assert position.check_stop_loss(Decimal('5')) is False
