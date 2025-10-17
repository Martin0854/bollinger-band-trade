"""
Trade model (data-model.md Entity 3).
Immutable audit record of executed trades with complete context.
Enhanced with auxiliary indicator data for Phase 1-4 features.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, Optional


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
        confidence_score: Optional confidence score (0-100) from enhanced signal (Phase 3)
        volume_pass: Optional volume filter pass/fail (Phase 3)
        rsi_pass: Optional RSI filter pass/fail (Phase 3)
        macd_pass: Optional MACD filter pass/fail (Phase 3)
        atr_value: Optional ATR value at trade time (Phase 4)
        dynamic_stop_loss: Optional ATR-based stop-loss price (Phase 4)
        stop_loss_type: Optional stop-loss type - "FIXED" or "ATR_DYNAMIC" (Phase 4)
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
    # Phase 3: Confidence scoring fields (optional for backward compatibility)
    confidence_score: Optional[int] = None
    volume_pass: Optional[bool] = None
    rsi_pass: Optional[bool] = None
    macd_pass: Optional[bool] = None
    # Phase 4: ATR dynamic stop-loss fields (optional for backward compatibility)
    atr_value: Optional[float] = None
    dynamic_stop_loss: Optional[Decimal] = None
    stop_loss_type: Optional[str] = None

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
            'realized_pnl': float(self.realized_pnl) if self.realized_pnl is not None else None,
            # Phase 3: Confidence fields
            'confidence_score': self.confidence_score,
            'volume_pass': self.volume_pass,
            'rsi_pass': self.rsi_pass,
            'macd_pass': self.macd_pass,
            # Phase 4: ATR dynamic stop-loss fields
            'atr_value': self.atr_value,
            'dynamic_stop_loss': float(self.dynamic_stop_loss) if self.dynamic_stop_loss is not None else None,
            'stop_loss_type': self.stop_loss_type
        }


# ========================================================================
# Enhanced Trade Model (Entity 6: EnhancedSignal)
# Extends base Trade with auxiliary indicator data and confidence scoring
# ========================================================================


@dataclass(frozen=True)
class EnhancedSignal:
    """
    Entity 6: EnhancedSignal represents a trading signal with auxiliary indicator data.

    Extends the base Trade concept with:
    - Confidence score (0-100 points)
    - Individual filter pass/fail status
    - Indicator values at signal generation time
    - Dynamic stop-loss price (ATR-based)

    Attributes:
        stock_code: 6-digit Korean stock code
        signal_type: "BUY" or "SELL"
        execution_price: Price at signal generation
        execution_timestamp: Timezone-aware timestamp (Asia/Seoul)
        reason: Signal generation reason
        bollinger_values: Dict with 'upper', 'middle', 'lower' band values
        confidence_score: Signal confidence (0-100 points)
        volume_pass: Volume filter passed
        rsi_pass: RSI filter passed
        macd_pass: MACD filter passed
        rsi_value: RSI value at signal time (if calculated)
        macd_value: MACD histogram value at signal time (if calculated)
        atr_value: ATR value at signal time (if calculated)
        dynamic_stop_loss: ATR-based stop-loss price (if enabled)
    """
    stock_code: str
    signal_type: str  # "BUY" or "SELL"
    execution_price: Decimal
    execution_timestamp: datetime
    reason: str
    bollinger_values: Dict[str, Decimal]

    # Enhanced fields (Phase 1-4)
    confidence_score: int  # 0-100 points
    volume_pass: bool = False
    rsi_pass: bool = False
    macd_pass: bool = False

    # Indicator values at signal time
    rsi_value: Optional[float] = None
    macd_value: Optional[float] = None  # Histogram value
    atr_value: Optional[float] = None

    # Dynamic stop-loss (Phase 4)
    dynamic_stop_loss: Optional[Decimal] = None

    def __post_init__(self):
        """Validate EnhancedSignal fields."""
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

        # Validate confidence_score in range
        if not (0 <= self.confidence_score <= 100):
            raise ValueError(
                f"confidence_score must be 0-100, got: {self.confidence_score}"
            )

        # Validate signal_type
        if self.signal_type not in ["BUY", "SELL"]:
            raise ValueError(
                f"signal_type must be BUY or SELL, got: '{self.signal_type}'"
            )

        # Validate dynamic_stop_loss < execution_price (if set)
        if self.dynamic_stop_loss is not None and self.dynamic_stop_loss >= self.execution_price:
            raise ValueError(
                f"dynamic_stop_loss ({self.dynamic_stop_loss}) must be less than "
                f"execution_price ({self.execution_price})"
            )

    def to_log_dict(self) -> Dict:
        """
        Convert EnhancedSignal to JSON-serializable dict for logging.

        Returns:
            Dictionary suitable for JSON logging and database insertion
        """
        return {
            'timestamp': self.execution_timestamp.isoformat(),
            'stock_code': self.stock_code,
            'signal_type': self.signal_type,
            'price': float(self.execution_price),
            'reason': self.reason,
            'bollinger_upper': float(self.bollinger_values.get('upper', 0)),
            'bollinger_middle': float(self.bollinger_values.get('middle', 0)),
            'bollinger_lower': float(self.bollinger_values.get('lower', 0)),
            # Enhanced fields
            'confidence_score': self.confidence_score,
            'volume_pass': self.volume_pass,
            'rsi_pass': self.rsi_pass,
            'macd_pass': self.macd_pass,
            'rsi_value': self.rsi_value,
            'macd_value': self.macd_value,
            'atr_value': self.atr_value,
            'dynamic_stop_loss': float(self.dynamic_stop_loss) if self.dynamic_stop_loss else None,
        }
