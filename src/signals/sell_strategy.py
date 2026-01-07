"""
Common sell strategy logic.
Used by both backtest engine and web API signal scanner.
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SellReason(Enum):
    STOP_LOSS = "stop_loss_hit"
    TAKE_PROFIT = "take_profit_target_hit"
    TREND_BROKEN = "trend_broken_middle_band"


@dataclass
class SellSignal:
    should_sell: bool
    reason: Optional[SellReason]
    sell_ratio: float  # 1.0 = full, 0.5 = half
    sell_quantity: int
    priority: int  # 1 = highest


@dataclass
class SellStrategyConfig:
    stop_loss_pct: float = 5.0
    take_profit_pct: float = 10.0
    take_profit_ratio: float = 0.5

    def __post_init__(self):
        if not 1.0 <= self.stop_loss_pct <= 20.0:
            raise ValueError("stop_loss_pct must be between 1.0 and 20.0")
        if not 5.0 <= self.take_profit_pct <= 50.0:
            raise ValueError("take_profit_pct must be between 5.0 and 50.0")
        if not 0.1 <= self.take_profit_ratio <= 1.0:
            raise ValueError("take_profit_ratio must be between 0.1 and 1.0")


def evaluate_sell_conditions(
    pnl_pct: float,
    current_price: float,
    bb_middle: Optional[float],
    quantity: int,
    partial_take_profit_executed: bool,
    config: SellStrategyConfig,
) -> SellSignal:
    """
    Evaluate sell conditions with priority-based logic.

    Priority order:
    - P1: Stop-loss (pnl <= -stop_loss_pct) -> 100% sell
    - P2: Take-profit (pnl >= +take_profit_pct, not yet executed) -> partial sell
    - P3: Trend breakdown (close < BB_Middle) -> 100% sell

    Args:
        pnl_pct: Current profit/loss percentage
        current_price: Current stock price
        bb_middle: Bollinger Band middle value (can be None)
        quantity: Current position quantity
        partial_take_profit_executed: Whether take-profit was already executed
        config: Sell strategy configuration

    Returns:
        SellSignal with sell decision details
    """
    # P1: Stop-loss check (highest priority)
    if pnl_pct <= -config.stop_loss_pct:
        return SellSignal(
            should_sell=True,
            reason=SellReason.STOP_LOSS,
            sell_ratio=1.0,
            sell_quantity=quantity,
            priority=1,
        )

    # P2: Take-profit check (partial sell)
    if pnl_pct >= config.take_profit_pct and not partial_take_profit_executed:
        sell_qty = max(1, math.ceil(quantity * config.take_profit_ratio))
        return SellSignal(
            should_sell=True,
            reason=SellReason.TAKE_PROFIT,
            sell_ratio=config.take_profit_ratio,
            sell_quantity=sell_qty,
            priority=2,
        )

    # P3: Trend breakdown check (full exit)
    if bb_middle is not None and current_price < bb_middle:
        return SellSignal(
            should_sell=True,
            reason=SellReason.TREND_BROKEN,
            sell_ratio=1.0,
            sell_quantity=quantity,
            priority=3,
        )

    return SellSignal(
        should_sell=False,
        reason=None,
        sell_ratio=0.0,
        sell_quantity=0,
        priority=0,
    )
