"""
Risk management controls.
Implements position sizing, stop-loss checking, and portfolio constraints.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional


@dataclass
class RiskLimits:
    """
    Configuration for risk management parameters.

    Attributes:
        stop_loss_percent: Maximum loss per position (default 5%)
        max_position_percent: Maximum allocation per stock (default 30%)
        max_positions: Maximum number of concurrent positions (default 5)
    """
    stop_loss_percent: Decimal = Decimal('5')
    max_position_percent: Decimal = Decimal('30')
    max_positions: int = 5


def check_stop_loss(
    purchase_price: Decimal,
    current_price: Decimal,
    stop_loss_percent: Decimal
) -> bool:
    """
    Check if position has hit stop-loss threshold.

    Args:
        purchase_price: Original purchase price
        current_price: Current market price
        stop_loss_percent: Stop-loss threshold (e.g., 5 for 5%)

    Returns:
        True if stop-loss triggered, False otherwise

    Raises:
        ValueError: If stop_loss_percent <= 0
    """
    if stop_loss_percent <= 0:
        raise ValueError(f"stop_loss_percent must be positive: {stop_loss_percent}")

    # Calculate loss percentage
    loss_pct = ((purchase_price - current_price) / purchase_price) * 100

    # Trigger if loss >= threshold
    return loss_pct >= stop_loss_percent


def calculate_position_size(
    portfolio_value: Decimal,
    stock_price: Decimal,
    max_position_percent: Decimal
) -> int:
    """
    Calculate number of shares to buy based on position sizing rules.

    Args:
        portfolio_value: Total portfolio value
        stock_price: Current stock price
        max_position_percent: Maximum allocation percentage (e.g., 30 for 30%)

    Returns:
        Number of shares to buy (integer)

    Raises:
        ValueError: If max_position_percent not in (0, 100]
    """
    if not (0 < max_position_percent <= 100):
        raise ValueError(
            f"max_position_percent must be in (0, 100]: {max_position_percent}"
        )

    # Calculate max allocation in currency
    max_allocation = portfolio_value * (max_position_percent / 100)

    # Calculate number of shares (floor division)
    quantity = int(max_allocation / stock_price)

    return quantity


def can_open_new_position(
    current_position_count: int,
    max_positions: int
) -> bool:
    """
    Check if portfolio can open a new position.

    Args:
        current_position_count: Number of currently open positions
        max_positions: Maximum allowed positions

    Returns:
        True if can open new position, False otherwise
    """
    return current_position_count < max_positions


def validate_sufficient_cash(
    cash_balance: Decimal,
    required_cash: Decimal
) -> None:
    """
    Validate that sufficient cash is available for trade.

    Args:
        cash_balance: Current cash balance
        required_cash: Required cash for trade

    Raises:
        ValueError: If insufficient cash
    """
    if cash_balance < required_cash:
        raise ValueError(
            f"Insufficient cash: have {cash_balance}, need {required_cash}"
        )


def calculate_trade_value(
    quantity: int,
    price: Decimal
) -> Decimal:
    """
    Calculate total trade value.

    Args:
        quantity: Number of shares
        price: Price per share

    Returns:
        Total trade value
    """
    return quantity * price


def check_positions_for_stop_loss(
    positions: List,
    stop_loss_percent: Decimal
) -> List:
    """
    Check all positions for stop-loss triggers.

    Args:
        positions: List of Position objects
        stop_loss_percent: Stop-loss threshold

    Returns:
        List of positions that should be closed
    """
    triggered = []

    for position in positions:
        if position.check_stop_loss(stop_loss_percent):
            triggered.append(position)

    return triggered


def calculate_portfolio_concentration(
    positions: List,
    total_portfolio_value: Decimal
) -> dict:
    """
    Calculate concentration percentage for each position.

    Args:
        positions: List of Position objects
        total_portfolio_value: Total portfolio value

    Returns:
        Dict mapping stock_code to concentration percentage
    """
    concentration = {}

    for position in positions:
        if total_portfolio_value > 0:
            pct = (position.market_value / total_portfolio_value) * 100
            concentration[position.stock_code] = float(pct)
        else:
            concentration[position.stock_code] = 0.0

    return concentration


def calculate_dynamic_stop_loss(
    entry_price: Decimal,
    atr_value: Optional[float],
    atr_multiplier: float = 2.0,
    fixed_stop_loss_percent: Decimal = Decimal('5')
) -> Decimal:
    """
    Calculate stop-loss price using ATR-based dynamic method or fixed percentage.

    ATR-based stop-loss adapts to market volatility:
    - High volatility stocks get wider stops (fewer false stops)
    - Low volatility stocks get tighter stops (better protection)

    Args:
        entry_price: Position entry price
        atr_value: Average True Range value (None if unavailable)
        atr_multiplier: Multiplier for ATR (default 2.0)
        fixed_stop_loss_percent: Fallback fixed percentage (default 5%)

    Returns:
        Stop-loss price (Decimal)

    Examples:
        >>> # High volatility: ATR = 2000, entry = 75000
        >>> calculate_dynamic_stop_loss(Decimal('75000'), 2000.0, 2.0)
        Decimal('71000')  # 75000 - (2000 * 2) = wider stop

        >>> # Low volatility: ATR = 500, entry = 75000
        >>> calculate_dynamic_stop_loss(Decimal('75000'), 500.0, 2.0)
        Decimal('74000')  # 75000 - (500 * 2) = tighter stop

        >>> # No ATR data: fallback to fixed 5%
        >>> calculate_dynamic_stop_loss(Decimal('75000'), None, 2.0)
        Decimal('71250')  # 75000 * 0.95
    """
    # Use ATR-based dynamic stop if available
    if atr_value is not None and atr_value > 0:
        atr_distance = Decimal(str(atr_value)) * Decimal(str(atr_multiplier))
        stop_price = entry_price - atr_distance

        # Ensure stop price is positive
        if stop_price <= 0:
            stop_price = entry_price * (Decimal('1') - fixed_stop_loss_percent / Decimal('100'))

        return stop_price

    # Fallback to fixed percentage stop-loss
    return entry_price * (Decimal('1') - fixed_stop_loss_percent / Decimal('100'))


def check_dynamic_stop_loss(
    entry_price: Decimal,
    current_price: Decimal,
    stop_loss_price: Decimal
) -> bool:
    """
    Check if position has hit dynamic stop-loss price.

    Args:
        entry_price: Original entry price
        current_price: Current market price
        stop_loss_price: Predetermined stop-loss price

    Returns:
        True if stop-loss triggered, False otherwise

    Examples:
        >>> check_dynamic_stop_loss(Decimal('75000'), Decimal('70000'), Decimal('71000'))
        True  # Current price below stop

        >>> check_dynamic_stop_loss(Decimal('75000'), Decimal('72000'), Decimal('71000'))
        False  # Current price above stop
    """
    return current_price <= stop_loss_price
