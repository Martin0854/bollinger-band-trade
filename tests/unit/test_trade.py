"""
Unit tests for Trade model (data-model.md Entity 3).
Tests immutability, BUY has entry_reason, SELL has exit_reason+realized_pnl, to_log_dict.

These tests MUST FAIL initially (TDD) until src/models/trade.py is implemented.
"""

import pytest
from decimal import Decimal
from datetime import datetime
import pytz


def test_trade_buy_creation():
    """Test BUY trade can be created with entry_reason."""
    from src.models.trade import Trade, TradeAction

    trade = Trade(
        stock_code="005930",
        action=TradeAction.BUY,
        execution_price=Decimal('60000'),
        quantity=10,
        execution_timestamp=datetime(2024, 1, 15, 9, 0, 0, tzinfo=pytz.timezone('Asia/Seoul')),
        band_width_at_entry=Decimal('5000'),
        bollinger_values={'upper': Decimal('65000'), 'middle': Decimal('60000'), 'lower': Decimal('55000')},
        portfolio_value_before=Decimal('10000000'),
        portfolio_value_after=Decimal('9400000'),
        cash_after=Decimal('9400000'),
        entry_reason="squeeze_expansion_buy"
    )

    assert trade.action == TradeAction.BUY
    assert trade.entry_reason == "squeeze_expansion_buy"
    assert trade.exit_reason is None
    assert trade.realized_pnl is None


def test_trade_sell_creation():
    """Test SELL trade can be created with exit_reason and realized_pnl."""
    from src.models.trade import Trade, TradeAction

    trade = Trade(
        stock_code="005930",
        action=TradeAction.SELL,
        execution_price=Decimal('65000'),
        quantity=10,
        execution_timestamp=datetime(2024, 2, 15, 15, 30, 0, tzinfo=pytz.timezone('Asia/Seoul')),
        band_width_at_entry=Decimal('6000'),
        bollinger_values={'upper': Decimal('68000'), 'middle': Decimal('63000'), 'lower': Decimal('58000')},
        portfolio_value_before=Decimal('9450000'),
        portfolio_value_after=Decimal('10100000'),
        cash_after=Decimal('10100000'),
        exit_reason="band_upper_exit",
        realized_pnl=Decimal('50000')
    )

    assert trade.action == TradeAction.SELL
    assert trade.exit_reason == "band_upper_exit"
    assert trade.realized_pnl == Decimal('50000')
    assert trade.entry_reason is None


def test_trade_buy_must_have_entry_reason():
    """Test BUY trade validation requires entry_reason."""
    from src.models.trade import Trade, TradeAction

    with pytest.raises(ValueError, match="entry_reason"):
        Trade(
            stock_code="005930",
            action=TradeAction.BUY,
            execution_price=Decimal('60000'),
            quantity=10,
            execution_timestamp=datetime(2024, 1, 15, 9, 0, 0, tzinfo=pytz.timezone('Asia/Seoul')),
            band_width_at_entry=Decimal('5000'),
            bollinger_values={'upper': Decimal('65000'), 'middle': Decimal('60000'), 'lower': Decimal('55000')},
            portfolio_value_before=Decimal('10000000'),
            portfolio_value_after=Decimal('9400000'),
            cash_after=Decimal('9400000'),
            # Missing entry_reason - should fail
        )


def test_trade_sell_must_have_exit_reason():
    """Test SELL trade validation requires exit_reason."""
    from src.models.trade import Trade, TradeAction

    with pytest.raises(ValueError, match="exit_reason"):
        Trade(
            stock_code="005930",
            action=TradeAction.SELL,
            execution_price=Decimal('65000'),
            quantity=10,
            execution_timestamp=datetime(2024, 2, 15, 15, 30, 0, tzinfo=pytz.timezone('Asia/Seoul')),
            band_width_at_entry=Decimal('6000'),
            bollinger_values={'upper': Decimal('68000'), 'middle': Decimal('63000'), 'lower': Decimal('58000')},
            portfolio_value_before=Decimal('9450000'),
            portfolio_value_after=Decimal('10100000'),
            cash_after=Decimal('10100000'),
            # Missing exit_reason - should fail
            realized_pnl=Decimal('50000')
        )


def test_trade_price_must_be_positive():
    """Test Trade validates execution_price > 0."""
    from src.models.trade import Trade, TradeAction

    with pytest.raises(ValueError, match="positive"):
        Trade(
            stock_code="005930",
            action=TradeAction.BUY,
            execution_price=Decimal('0'),  # Invalid
            quantity=10,
            execution_timestamp=datetime(2024, 1, 15, 9, 0, 0, tzinfo=pytz.timezone('Asia/Seoul')),
            band_width_at_entry=Decimal('5000'),
            bollinger_values={'upper': Decimal('65000'), 'middle': Decimal('60000'), 'lower': Decimal('55000')},
            portfolio_value_before=Decimal('10000000'),
            portfolio_value_after=Decimal('9400000'),
            cash_after=Decimal('9400000'),
            entry_reason="squeeze_expansion_buy"
        )


def test_trade_quantity_must_be_positive():
    """Test Trade validates quantity > 0."""
    from src.models.trade import Trade, TradeAction

    with pytest.raises(ValueError, match="positive"):
        Trade(
            stock_code="005930",
            action=TradeAction.BUY,
            execution_price=Decimal('60000'),
            quantity=0,  # Invalid
            execution_timestamp=datetime(2024, 1, 15, 9, 0, 0, tzinfo=pytz.timezone('Asia/Seoul')),
            band_width_at_entry=Decimal('5000'),
            bollinger_values={'upper': Decimal('65000'), 'middle': Decimal('60000'), 'lower': Decimal('55000')},
            portfolio_value_before=Decimal('10000000'),
            portfolio_value_after=Decimal('9400000'),
            cash_after=Decimal('9400000'),
            entry_reason="squeeze_expansion_buy"
        )


def test_trade_to_log_dict():
    """Test to_log_dict converts Trade to JSON-serializable dict."""
    from src.models.trade import Trade, TradeAction

    trade = Trade(
        stock_code="005930",
        action=TradeAction.BUY,
        execution_price=Decimal('60000'),
        quantity=10,
        execution_timestamp=datetime(2024, 1, 15, 9, 0, 0, tzinfo=pytz.timezone('Asia/Seoul')),
        band_width_at_entry=Decimal('5000'),
        bollinger_values={'upper': Decimal('65000'), 'middle': Decimal('60000'), 'lower': Decimal('55000')},
        portfolio_value_before=Decimal('10000000'),
        portfolio_value_after=Decimal('9400000'),
        cash_after=Decimal('9400000'),
        entry_reason="squeeze_expansion_buy"
    )

    log_dict = trade.to_log_dict()

    assert 'trade_id' in log_dict
    assert log_dict['stock_code'] == "005930"
    assert log_dict['action'] == "buy"
    assert log_dict['quantity'] == 10
    assert log_dict['price'] == 60000.0
    assert log_dict['reason'] == "squeeze_expansion_buy"
    assert log_dict['bollinger_upper'] == 65000.0
    assert log_dict['bollinger_middle'] == 60000.0
    assert log_dict['bollinger_lower'] == 55000.0
    assert log_dict['band_width'] == 5000.0


def test_trade_is_immutable():
    """Test Trade is immutable (frozen dataclass)."""
    from src.models.trade import Trade, TradeAction

    trade = Trade(
        stock_code="005930",
        action=TradeAction.BUY,
        execution_price=Decimal('60000'),
        quantity=10,
        execution_timestamp=datetime(2024, 1, 15, 9, 0, 0, tzinfo=pytz.timezone('Asia/Seoul')),
        band_width_at_entry=Decimal('5000'),
        bollinger_values={'upper': Decimal('65000'), 'middle': Decimal('60000'), 'lower': Decimal('55000')},
        portfolio_value_before=Decimal('10000000'),
        portfolio_value_after=Decimal('9400000'),
        cash_after=Decimal('9400000'),
        entry_reason="squeeze_expansion_buy"
    )

    # Attempting to modify should raise error
    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        trade.quantity = 20
