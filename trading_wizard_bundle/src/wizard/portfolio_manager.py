"""
Portfolio JSON persistence manager.
Handles loading, saving, and state management for daily wizard.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class WizardPosition:
    """Position for daily wizard."""

    stock_code: str
    quantity: int
    entry_price: float
    entry_date: str
    entry_reason: str
    confidence_score: Optional[int] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "WizardPosition":
        return cls(**data)


@dataclass
class TradeRecord:
    """Completed trade record."""

    date: str
    stock_code: str
    action: str  # "BUY" or "SELL"
    price: float
    quantity: int
    reason: str
    realized_pnl: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TradeRecord":
        return cls(**data)


@dataclass
class PendingOrder:
    """Pending order for user to execute."""

    recommendation_date: str
    stock_code: str
    stock_name: str  # Company name for easy identification
    action: str  # "BUY" or "SELL"
    recommended_price: float
    quantity: int
    reason_detail: str  # Detailed explanation of why this trade is recommended
    indicators: dict  # Technical indicators at the time of recommendation
    actual_price: Optional[float] = None
    executed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PendingOrder":
        return cls(**data)


@dataclass
class WizardPortfolioState:
    """Complete portfolio state."""

    initial_capital: float
    cash_balance: float
    start_date: str
    last_updated: str
    positions: List[WizardPosition] = field(default_factory=list)
    trade_history: List[TradeRecord] = field(default_factory=list)
    pending_orders: List[PendingOrder] = field(default_factory=list)
    last_run_output: str = ""  # Store the last wizard run output

    def to_dict(self) -> dict:
        return {
            "initial_capital": self.initial_capital,
            "cash_balance": self.cash_balance,
            "start_date": self.start_date,
            "last_updated": self.last_updated,
            "positions": [p.to_dict() for p in self.positions],
            "trade_history": [t.to_dict() for t in self.trade_history],
            "pending_orders": [o.to_dict() for o in self.pending_orders],
            "last_run_output": self.last_run_output,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WizardPortfolioState":
        return cls(
            initial_capital=data["initial_capital"],
            cash_balance=data["cash_balance"],
            start_date=data["start_date"],
            last_updated=data["last_updated"],
            positions=[
                WizardPosition.from_dict(p) for p in data.get("positions", [])
            ],
            trade_history=[
                TradeRecord.from_dict(t) for t in data.get("trade_history", [])
            ],
            pending_orders=[
                PendingOrder.from_dict(o) for o in data.get("pending_orders", [])
            ],
            last_run_output=data.get("last_run_output", ""),
        )

    @classmethod
    def initialize_new(
        cls, initial_capital: float = 1_000_000, start_date: str = "2026-01-05"
    ) -> "WizardPortfolioState":
        """Create new portfolio with initial capital."""
        return cls(
            initial_capital=initial_capital,
            cash_balance=initial_capital,
            start_date=start_date,
            last_updated=datetime.now().isoformat(),
        )

    def get_position(self, stock_code: str) -> Optional[WizardPosition]:
        """Get position by stock code."""
        for pos in self.positions:
            if pos.stock_code == stock_code:
                return pos
        return None

    def has_position(self, stock_code: str) -> bool:
        """Check if stock is in portfolio."""
        return self.get_position(stock_code) is not None


class PortfolioManager:
    """Manages portfolio state persistence."""

    def __init__(self, state_file: str = "portfolio_state.json"):
        self.state_file = Path(state_file)

    def exists(self) -> bool:
        """Check if state file exists."""
        return self.state_file.exists()

    def load(self) -> WizardPortfolioState:
        """Load existing state from JSON file."""
        if not self.state_file.exists():
            raise FileNotFoundError(f"Portfolio state file not found: {self.state_file}")

        with open(self.state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return WizardPortfolioState.from_dict(data)

    def load_or_create(
        self, initial_capital: float = 1_000_000, start_date: str = "2026-01-05"
    ) -> WizardPortfolioState:
        """Load existing state or create new one."""
        if self.state_file.exists():
            return self.load()
        else:
            return WizardPortfolioState.initialize_new(initial_capital, start_date)

    def save(self, state: WizardPortfolioState) -> None:
        """Save state to JSON file."""
        state.last_updated = datetime.now().isoformat()
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)

    def process_pending_orders(self, state: WizardPortfolioState) -> List[str]:
        """
        Process pending orders that user marked as executed.
        Returns list of messages describing what was processed.
        """
        messages = []
        processed_indices = []

        for i, order in enumerate(state.pending_orders):
            if order.executed and order.actual_price is not None:
                if order.action == "BUY":
                    # Add position
                    position = WizardPosition(
                        stock_code=order.stock_code,
                        quantity=order.quantity,
                        entry_price=order.actual_price,
                        entry_date=order.recommendation_date,
                        entry_reason="squeeze_breakout_buy",
                    )
                    state.positions.append(position)

                    # Deduct cash
                    total_cost = order.actual_price * order.quantity
                    state.cash_balance -= total_cost

                    # Record trade
                    trade = TradeRecord(
                        date=order.recommendation_date,
                        stock_code=order.stock_code,
                        action="BUY",
                        price=order.actual_price,
                        quantity=order.quantity,
                        reason="squeeze_breakout_buy",
                    )
                    state.trade_history.append(trade)
                    messages.append(
                        f"BUY: {order.stock_code} x {order.quantity} @ {order.actual_price:,.0f} "
                        f"(Total: {total_cost:,.0f} KRW)"
                    )
                    processed_indices.append(i)

                elif order.action == "SELL":
                    # Find and remove position
                    for j, pos in enumerate(state.positions):
                        if pos.stock_code == order.stock_code:
                            realized_pnl = (
                                order.actual_price - pos.entry_price
                            ) * order.quantity
                            total_proceeds = order.actual_price * order.quantity
                            state.cash_balance += total_proceeds

                            # Record trade
                            trade = TradeRecord(
                                date=order.recommendation_date,
                                stock_code=order.stock_code,
                                action="SELL",
                                price=order.actual_price,
                                quantity=order.quantity,
                                reason="wizard_sell",
                                realized_pnl=realized_pnl,
                            )
                            state.trade_history.append(trade)
                            state.positions.pop(j)

                            pnl_str = f"+{realized_pnl:,.0f}" if realized_pnl >= 0 else f"{realized_pnl:,.0f}"
                            messages.append(
                                f"SELL: {order.stock_code} x {order.quantity} @ {order.actual_price:,.0f} "
                                f"(PnL: {pnl_str} KRW)"
                            )
                            processed_indices.append(i)
                            break

        # Remove processed orders (in reverse to preserve indices)
        for i in sorted(processed_indices, reverse=True):
            state.pending_orders.pop(i)

        return messages

    def calculate_portfolio_value(
        self, state: WizardPortfolioState, current_prices: dict[str, float]
    ) -> dict:
        """
        Calculate current portfolio value with market prices.

        Args:
            state: Current portfolio state
            current_prices: Dict of stock_code -> current_price

        Returns:
            Dict with portfolio metrics
        """
        positions_value = 0.0
        unrealized_pnl = 0.0

        for pos in state.positions:
            current_price = current_prices.get(pos.stock_code, pos.entry_price)
            market_value = current_price * pos.quantity
            positions_value += market_value
            unrealized_pnl += (current_price - pos.entry_price) * pos.quantity

        total_value = state.cash_balance + positions_value
        total_return_pct = (
            (total_value - state.initial_capital) / state.initial_capital
        ) * 100

        # Calculate realized P&L from trade history
        realized_pnl = sum(
            t.realized_pnl for t in state.trade_history if t.realized_pnl is not None
        )

        return {
            "initial_capital": state.initial_capital,
            "cash_balance": state.cash_balance,
            "positions_value": positions_value,
            "total_value": total_value,
            "unrealized_pnl": unrealized_pnl,
            "realized_pnl": realized_pnl,
            "total_return_pct": total_return_pct,
            "position_count": len(state.positions),
        }
