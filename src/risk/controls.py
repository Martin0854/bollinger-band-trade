"""
Risk management controls.
Implements position sizing, stop-loss checking, and portfolio constraints.
"""

from decimal import Decimal
from typing import List
from dataclasses import dataclass


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
