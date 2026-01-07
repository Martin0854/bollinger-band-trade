"""
Portfolio and Position models (data-model.md Entities 1 & 2).
Implements portfolio management with positions, cash tracking, and equity curve.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple


@dataclass
class Position:
    """
    Entity 2: Position represents a stock holding in the portfolio.

    Attributes:
        stock_code: 6-digit Korean stock code (e.g., "005930" for Samsung)
        quantity: Number of shares held (must be > 0)
        purchase_price: Price per share at purchase (must be > 0)
        purchase_date: Date when position was opened
        entry_reason: Reason for entering position (e.g., "squeeze_expansion_buy")
        current_price: Current market price (updated during backtest)
        dynamic_stop_loss: Optional ATR-based stop-loss price (Phase 4)

    Computed Properties:
        cost_basis: Total cost = quantity * purchase_price
        market_value: Current value = quantity * current_price
        unrealized_pnl: Profit/Loss = (current_price - purchase_price) * quantity
        unrealized_pnl_pct: PnL percentage = unrealized_pnl / cost_basis * 100
    """

    stock_code: str
    quantity: int
    purchase_price: Decimal
    purchase_date: datetime
    entry_reason: str
    current_price: Decimal = field(default=None)
    dynamic_stop_loss: Optional[Decimal] = field(default=None)
    atr_value: Optional[float] = field(default=None)
    partial_take_profit_executed: bool = field(default=False)

    def __post_init__(self):
        """Validate position fields."""
        # Validate stock_code
        from src.utils.validation import validate_stock_code

        validate_stock_code(self.stock_code)

        # Validate quantity > 0
        if self.quantity <= 0:
            raise ValueError(f"quantity must be positive, got: {self.quantity}")

        # Validate purchase_price > 0
        if self.purchase_price <= 0:
            raise ValueError(f"purchase_price must be positive, got: {self.purchase_price}")

        # Initialize current_price to purchase_price if not set
        if self.current_price is None:
            self.current_price = self.purchase_price

    @property
    def cost_basis(self) -> Decimal:
        """Total cost = quantity * purchase_price."""
        return self.quantity * self.purchase_price

    @property
    def market_value(self) -> Decimal:
        """Current market value = quantity * current_price."""
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> Decimal:
        """Unrealized profit/loss = (current_price - purchase_price) * quantity."""
        return (self.current_price - self.purchase_price) * self.quantity

    @property
    def unrealized_pnl_pct(self) -> Decimal:
        """Unrealized PnL percentage = unrealized_pnl / cost_basis * 100."""
        if self.cost_basis == 0:
            return Decimal("0")
        return (self.unrealized_pnl / self.cost_basis) * 100

    def check_stop_loss(self, stop_loss_percent: Decimal) -> bool:
        """
        Check if position should be closed due to stop-loss.

        Prioritizes dynamic stop-loss if set, otherwise uses fixed percentage.

        Args:
            stop_loss_percent: Stop-loss threshold (e.g., 5 for 5%)

        Returns:
            True if current loss >= stop_loss_percent or price <= dynamic_stop_loss
        """
        # Check dynamic stop-loss first (Phase 4: ATR-based)
        if self.dynamic_stop_loss is not None:
            if self.current_price <= self.dynamic_stop_loss:
                return True

        # Fallback to fixed percentage stop-loss
        loss_pct = abs(self.unrealized_pnl_pct)

        # If losing money and loss >= threshold
        if self.unrealized_pnl < 0 and loss_pct >= stop_loss_percent:
            return True

        return False


@dataclass
class Portfolio:
    """
    Entity 1: Portfolio represents the trading account state.

    Attributes:
        cash_balance: Available cash in KRW (must be >= 0)
        initial_capital: Starting capital
        positions: Dictionary of stock_code -> Position
        equity_curve: List of (timestamp, total_value) tuples

    Computed Properties:
        total_value: Sum of cash + all position market values
        total_return_pct: (total_value - initial_capital) / initial_capital * 100
    """

    cash_balance: Decimal
    initial_capital: Decimal
    positions: Dict[str, Position] = field(default_factory=dict)
    equity_curve: List[Tuple[datetime, Decimal]] = field(default_factory=list)

    @property
    def total_value(self) -> Decimal:
        """
        Total portfolio value = cash + sum of all position market values.
        """
        positions_value = sum(position.market_value for position in self.positions.values())
        return self.cash_balance + positions_value

    @property
    def total_return_pct(self) -> Decimal:
        """
        Total return percentage = (total_value - initial_capital) / initial_capital * 100.
        """
        if self.initial_capital == 0:
            return Decimal("0")
        return ((self.total_value - self.initial_capital) / self.initial_capital) * 100

    def validate_cash_nonnegative(self) -> None:
        """
        Validate cash_balance >= 0 (constitutional requirement).

        Raises:
            ValueError: If cash_balance is negative
        """
        if self.cash_balance < 0:
            raise ValueError(f"cash_balance cannot be negative, got: {self.cash_balance}")

    def record_snapshot(self, timestamp: datetime) -> None:
        """
        Record current portfolio state to equity curve.

        Args:
            timestamp: Time of snapshot
        """
        self.equity_curve.append((timestamp, self.total_value))

    def add_position(self, position: Position) -> None:
        """
        Add a position to the portfolio.

        Args:
            position: Position to add

        Raises:
            ValueError: If position with same stock_code already exists
        """
        if position.stock_code in self.positions:
            raise ValueError(f"Position for {position.stock_code} already exists")
        self.positions[position.stock_code] = position

    def remove_position(self, stock_code: str) -> Optional[Position]:
        """
        Remove a position from the portfolio.

        Args:
            stock_code: Stock code of position to remove

        Returns:
            Removed position, or None if not found
        """
        return self.positions.pop(stock_code, None)

    def get_position(self, stock_code: str) -> Optional[Position]:
        """
        Get a position by stock code.

        Args:
            stock_code: Stock code to look up

        Returns:
            Position if found, None otherwise
        """
        return self.positions.get(stock_code)

    def update_position_prices(self, prices: Dict[str, Decimal]) -> None:
        """
        Update current prices for all positions.

        Args:
            prices: Dictionary of stock_code -> current_price
        """
        for stock_code, position in self.positions.items():
            if stock_code in prices:
                position.current_price = prices[stock_code]

    def get_positions_at_stop_loss(self, stop_loss_percent: Decimal) -> List[Position]:
        """
        Get all positions that have hit stop-loss threshold.

        Args:
            stop_loss_percent: Stop-loss threshold percentage

        Returns:
            List of positions that should be closed
        """
        return [
            position
            for position in self.positions.values()
            if position.check_stop_loss(stop_loss_percent)
        ]
