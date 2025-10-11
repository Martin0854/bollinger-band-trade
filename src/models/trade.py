"""
Trade model (data-model.md Entity 3).
Immutable audit record of executed trades with complete context.
"""

from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Dict, Optional
from enum import Enum
import uuid


class TradeAction(Enum):
    """Trade action type."""
    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True)
class Trade:
    """
    Entity 3: Trade represents an immutable record of an executed trade.

    This is a frozen dataclass (immutable) for audit integrity.

    Attributes:
        stock_code: 6-digit Korean stock code
        action: BUY or SELL
        execution_price: Price at which trade was executed
        quantity: Number of shares traded
        execution_timestamp: Timezone-aware timestamp (Asia/Seoul)
        band_width_at_entry: Bollinger Band width at trade time
        bollinger_values: Dict with 'upper', 'middle', 'lower' band values
        portfolio_value_before: Portfolio value before trade
        portfolio_value_after: Portfolio value after trade
        cash_after: Cash balance after trade
        entry_reason: Required for BUY trades (e.g., "squeeze_expansion_buy")
        exit_reason: Required for SELL trades (e.g., "band_upper_exit", "stop_loss")
        realized_pnl: Required for SELL trades (profit/loss realized)
        trade_id: Unique identifier (auto-generated UUID)
    """
    stock_code: str
    action: TradeAction
    execution_price: Decimal
    quantity: int
    execution_timestamp: datetime
    band_width_at_entry: Decimal
    bollinger_values: Dict[str, Decimal]
    portfolio_value_before: Decimal
    portfolio_value_after: Decimal
    cash_after: Decimal
    entry_reason: Optional[str] = None
    exit_reason: Optional[str] = None
    realized_pnl: Optional[Decimal] = None
    trade_id: str = None

    def __post_init__(self):
        """
        Validate trade fields and generate trade_id.

        Note: Since this is a frozen dataclass, we use object.__setattr__().
        """
        # Generate trade_id if not provided
        if self.trade_id is None:
            object.__setattr__(self, 'trade_id', str(uuid.uuid4()))

        # Validate stock_code: exactly 6 digits
        if not (self.stock_code.isdigit() and len(self.stock_code) == 6):
            raise ValueError(
                f"stock_code must be exactly 6 digits, got: '{self.stock_code}'"
            )

        # Validate execution_price > 0
        if self.execution_price <= 0:
            raise ValueError(
                f"execution_price must be positive, got: {self.execution_price}"
            )

        # Validate quantity > 0
        if self.quantity <= 0:
            raise ValueError(
                f"quantity must be positive, got: {self.quantity}"
            )

        # Validate BUY trades have entry_reason
        if self.action == TradeAction.BUY and not self.entry_reason:
            raise ValueError(
                "BUY trades must have entry_reason"
            )

        # Validate SELL trades have exit_reason
        if self.action == TradeAction.SELL and not self.exit_reason:
            raise ValueError(
                "SELL trades must have exit_reason"
            )

    def to_log_dict(self) -> Dict:
        """
        Convert Trade to JSON-serializable dict for logging.

        Returns:
            Dictionary suitable for JSON logging and database insertion
        """
        return {
            'trade_id': self.trade_id,
            'timestamp': self.execution_timestamp.isoformat(),
            'stock_code': self.stock_code,
            'action': self.action.value,
            'quantity': self.quantity,
            'price': float(self.execution_price),
            'reason': self.entry_reason if self.action == TradeAction.BUY else self.exit_reason,
            'bollinger_upper': float(self.bollinger_values.get('upper', 0)),
            'bollinger_middle': float(self.bollinger_values.get('middle', 0)),
            'bollinger_lower': float(self.bollinger_values.get('lower', 0)),
            'band_width': float(self.band_width_at_entry),
            'portfolio_value_before': float(self.portfolio_value_before),
            'portfolio_value_after': float(self.portfolio_value_after),
            'cash_after': float(self.cash_after),
            'realized_pnl': float(self.realized_pnl) if self.realized_pnl is not None else None
        }
