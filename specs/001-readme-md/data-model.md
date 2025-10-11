# Phase 1: Data Model Design

**Feature**: [001-readme-md](./spec.md)
**Date**: 2025-10-11
**Phase**: Design - Entity Definitions

## Overview

This document defines the 8 core entities extracted from the feature specification. Each entity represents a key domain concept in the Bollinger Band squeeze backtesting system. The models are designed to support the chosen technology stack (Python + Pydantic + pandas + vectorbt) and enforce constitutional principles (data integrity, auditability, configuration-driven design).

---

## Entity 1: Portfolio

**Purpose**: Represents the trader's account state at any point in time during backtesting. Tracks cash balance, open positions, and portfolio value history.

**Attributes**:
- `cash_balance` (Decimal): Current cash available for trading (KRW)
- `positions` (List[Position]): List of currently open positions
- `total_value` (Decimal): Cash + sum of all position market values (computed)
- `equity_curve` (List[Tuple[datetime, Decimal]]): Historical (timestamp, portfolio_value) pairs
- `initial_capital` (Decimal): Starting cash (immutable after initialization)
- `created_at` (datetime): Portfolio initialization timestamp

**Invariants**:
- `cash_balance >= 0` (cannot go negative)
- `total_value = cash_balance + sum(p.market_value for p in positions)`
- `equity_curve` is chronologically ordered

**Relationships**:
- Contains 0..N `Position` objects
- Generates `Trade` records when positions are opened/closed
- Configuration comes from `BacktestConfiguration`

**Implementation Notes** (Python):
```python
from decimal import Decimal
from datetime import datetime
from dataclasses import dataclass, field
from typing import List

@dataclass
class Portfolio:
    cash_balance: Decimal
    initial_capital: Decimal
    positions: List['Position'] = field(default_factory=list)
    equity_curve: List[Tuple[datetime, Decimal]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def total_value(self) -> Decimal:
        """Computed property: cash + position values"""
        position_values = sum(p.market_value for p in self.positions)
        return self.cash_balance + position_values

    def record_snapshot(self, timestamp: datetime):
        """Add current state to equity curve"""
        self.equity_curve.append((timestamp, self.total_value))

    def validate_cash_nonnegative(self):
        """Constitutional requirement: defensive validation"""
        if self.cash_balance < 0:
            raise ValueError(f"Cash balance cannot be negative: {self.cash_balance}")
```

**Storage**:
- In-memory during backtest (Python object)
- Equity curve exported to CSV/JSON for analysis
- Final state logged to SQLite `portfolio_snapshots` table

---

## Entity 2: Position

**Purpose**: Represents ownership of shares in a specific stock. Tracks entry details, current market value, and unrealized profit/loss.

**Attributes**:
- `stock_code` (str): 6-digit Korean stock code (e.g., "005930")
- `quantity` (int): Number of shares held (must be positive)
- `purchase_price` (Decimal): Price per share at entry (KRW)
- `purchase_date` (datetime): Timestamp when position was opened
- `current_price` (Decimal): Latest market price (updated each timestep)
- `entry_reason` (str): Signal that triggered buy (e.g., "squeeze_expansion_buy")
- `position_id` (UUID): Unique identifier

**Computed Properties**:
- `market_value = quantity * current_price`
- `cost_basis = quantity * purchase_price`
- `unrealized_pnl = market_value - cost_basis`
- `unrealized_pnl_pct = (unrealized_pnl / cost_basis) * 100`

**Invariants**:
- `quantity > 0` (positions with 0 shares are closed, not held)
- `purchase_price > 0`
- `stock_code` matches regex `^\d{6}$`

**Relationships**:
- Owned by one `Portfolio`
- Created by a `Trade` (buy action)
- Generates a `Trade` when closed (sell action)
- Uses `StockData` for current price updates

**Implementation Notes**:
```python
from decimal import Decimal
from datetime import datetime
from uuid import UUID, uuid4

@dataclass
class Position:
    stock_code: str
    quantity: int
    purchase_price: Decimal
    purchase_date: datetime
    entry_reason: str
    position_id: UUID = field(default_factory=uuid4)
    current_price: Decimal = field(default=Decimal(0))

    def __post_init__(self):
        """Validate invariants on creation"""
        if self.quantity <= 0:
            raise ValueError(f"Quantity must be positive: {self.quantity}")
        if self.purchase_price <= 0:
            raise ValueError(f"Purchase price must be positive: {self.purchase_price}")
        if not (self.stock_code.isdigit() and len(self.stock_code) == 6):
            raise ValueError(f"Invalid stock code format: {self.stock_code}")

    @property
    def market_value(self) -> Decimal:
        return self.quantity * self.current_price

    @property
    def cost_basis(self) -> Decimal:
        return self.quantity * self.purchase_price

    @property
    def unrealized_pnl(self) -> Decimal:
        return self.market_value - self.cost_basis

    @property
    def unrealized_pnl_pct(self) -> Decimal:
        return (self.unrealized_pnl / self.cost_basis) * 100

    def check_stop_loss(self, stop_loss_pct: Decimal) -> bool:
        """Check if position has hit stop-loss threshold"""
        return self.unrealized_pnl_pct <= -stop_loss_pct
```

---

## Entity 3: Trade

**Purpose**: Represents a completed transaction (buy or sell). Immutable record for audit trail and performance analysis.

**Attributes**:
- `trade_id` (UUID): Unique identifier
- `stock_code` (str): 6-digit stock code
- `action` (Enum): BUY or SELL
- `execution_price` (Decimal): Price per share (KRW)
- `quantity` (int): Number of shares transacted
- `execution_timestamp` (datetime): When trade occurred (with timezone)
- `entry_reason` (str | None): Why position was opened (e.g., "squeeze_expansion_buy") - only for BUY
- `exit_reason` (str | None): Why position was closed (e.g., "band_upper_exit", "stop_loss") - only for SELL
- `realized_pnl` (Decimal | None): Profit/loss for SELL (execution_price - purchase_price) * quantity
- `band_width_at_entry` (Decimal): Bollinger band width at trade time
- `bollinger_values` (Dict): {upper, middle, lower} band values at trade time
- `portfolio_value_before` (Decimal): Total portfolio value before trade
- `portfolio_value_after` (Decimal): Total portfolio value after trade
- `cash_after` (Decimal): Cash balance after trade

**Invariants**:
- `execution_price > 0`
- `quantity > 0`
- `action` is BUY or SELL
- BUY trades have `entry_reason`, not `exit_reason`
- SELL trades have `exit_reason` and `realized_pnl`

**Relationships**:
- Triggered by signals from `SignalGenerator`
- Creates/closes `Position` objects
- Updates `Portfolio` state
- References `BollingerBand` values at execution time

**Implementation Notes**:
```python
from enum import Enum
from typing import Dict, Optional

class TradeAction(str, Enum):
    BUY = "buy"
    SELL = "sell"

@dataclass(frozen=True)  # Immutable for audit integrity
class Trade:
    trade_id: UUID
    stock_code: str
    action: TradeAction
    execution_price: Decimal
    quantity: int
    execution_timestamp: datetime  # Timezone-aware
    band_width_at_entry: Decimal
    bollinger_values: Dict[str, Decimal]  # {upper, middle, lower}
    portfolio_value_before: Decimal
    portfolio_value_after: Decimal
    cash_after: Decimal
    entry_reason: Optional[str] = None
    exit_reason: Optional[str] = None
    realized_pnl: Optional[Decimal] = None

    def __post_init__(self):
        """Validate trade consistency"""
        if self.action == TradeAction.BUY and self.entry_reason is None:
            raise ValueError("BUY trades must have entry_reason")
        if self.action == TradeAction.SELL and self.exit_reason is None:
            raise ValueError("SELL trades must have exit_reason")
        if self.execution_price <= 0 or self.quantity <= 0:
            raise ValueError("Price and quantity must be positive")

    def to_log_dict(self) -> Dict:
        """Convert to structured log format (JSON-serializable)"""
        return {
            "trade_id": str(self.trade_id),
            "timestamp": self.execution_timestamp.isoformat(),
            "stock_code": self.stock_code,
            "action": self.action.value,
            "quantity": self.quantity,
            "price": float(self.execution_price),
            "reason": self.entry_reason or self.exit_reason,
            "bollinger_upper": float(self.bollinger_values['upper']),
            "bollinger_middle": float(self.bollinger_values['middle']),
            "bollinger_lower": float(self.bollinger_values['lower']),
            "band_width": float(self.band_width_at_entry),
            "portfolio_value_before": float(self.portfolio_value_before),
            "portfolio_value_after": float(self.portfolio_value_after),
            "cash_after": float(self.cash_after),
            "realized_pnl": float(self.realized_pnl) if self.realized_pnl else None
        }
```

**Storage**:
- SQLite `trade_log` table (all fields)
- JSON export for analysis
- CSV export for spreadsheet import

---

## Entity 4: StockData

**Purpose**: Represents historical market data for a single stock. Time-indexed OHLCV (Open, High, Low, Close, Volume) series.

**Attributes**:
- `stock_code` (str): 6-digit stock code
- `date_range` (Tuple[date, date]): (start_date, end_date) inclusive
- `data` (DataFrame): pandas DataFrame with DatetimeIndex (timezone-aware) and columns:
  - `Open` (float): Opening price
  - `High` (float): Highest price
  - `Low` (float): Lowest price
  - `Close` (float): Closing price (used for signal execution)
  - `Volume` (int): Number of shares traded
- `data_source` (str): Where data was fetched from (e.g., "FinanceDataReader", "pykrx")
- `fetched_at` (datetime): When data was retrieved
- `validation_status` (Enum): VALID, OUTLIERS_DETECTED, INCOMPLETE

**Invariants**:
- All OHLCV values > 0
- `Low <= Open, Close, High` for each row
- `High >= Open, Close, Low` for each row
- DatetimeIndex is chronologically ordered
- No missing dates within trading calendar

**Validation Rules** (from FR-003, FR-004):
- Completeness: Compare against KRX trading calendar, no gaps
- Outliers: Flag days with >20% price change without volume spike (>3σ volume)

**Relationships**:
- Consumed by `BollingerBand` for indicator calculation
- Used by `Portfolio` to update position `current_price`
- Validated by `DataValidator` before backtesting

**Implementation Notes**:
```python
import pandas as pd
from enum import Enum

class ValidationStatus(str, Enum):
    VALID = "valid"
    OUTLIERS_DETECTED = "outliers_detected"
    INCOMPLETE = "incomplete"

@dataclass
class StockData:
    stock_code: str
    date_range: Tuple[date, date]
    data: pd.DataFrame
    data_source: str
    fetched_at: datetime
    validation_status: ValidationStatus = ValidationStatus.VALID

    def __post_init__(self):
        """Validate OHLCV data integrity"""
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in self.data.columns for col in required_cols):
            raise ValueError(f"Missing required columns: {required_cols}")

        # Validate OHLC relationships
        if not (self.data['Low'] <= self.data['Close']).all():
            raise ValueError("Low must be <= Close")
        if not (self.data['High'] >= self.data['Close']).all():
            raise ValueError("High must be >= Close")
        if not (self.data[['Open', 'High', 'Low', 'Close', 'Volume']] > 0).all().all():
            raise ValueError("All OHLCV values must be positive")

        # Ensure timezone-aware index
        if self.data.index.tz is None:
            self.data.index = self.data.index.tz_localize('Asia/Seoul')

    def detect_outliers(self, price_threshold_pct: float = 20.0) -> pd.Series:
        """Detect anomalous price spikes (FR-004)"""
        daily_returns = self.data['Close'].pct_change() * 100
        volume_zscore = (self.data['Volume'] - self.data['Volume'].mean()) / self.data['Volume'].std()

        # Outlier: >20% price move without volume confirmation (z-score < 1)
        outliers = (daily_returns.abs() > price_threshold_pct) & (volume_zscore < 1)
        return outliers
```

**Storage**:
- Parquet files: `data/cache/{stock_code}_{start_date}_{end_date}.parquet`
- DataFrame serialization via PyArrow

---

## Entity 5: BollingerBand

**Purpose**: Represents calculated Bollinger Band indicator values for a specific stock on a specific date. Enables auditability of trade decisions.

**Attributes**:
- `stock_code` (str): 6-digit stock code
- `calculation_date` (datetime): Date of this calculation (timezone-aware)
- `middle_band` (Decimal): Simple moving average value
- `upper_band` (Decimal): Middle + (std_dev × multiplier)
- `lower_band` (Decimal): Middle - (std_dev × multiplier)
- `band_width` (Decimal): Upper - Lower (used for squeeze detection)
- `period` (int): Moving average window (e.g., 20)
- `std_dev_multiplier` (Decimal): Standard deviation multiplier (e.g., 2.0)
- `squeeze_status` (Enum): NONE, ACTIVE, EXPANDING

**Invariants**:
- `lower_band <= middle_band <= upper_band`
- `band_width = upper_band - lower_band`
- `band_width >= 0`

**Computed From**:
- `middle_band = SMA(Close, period)`
- `std_dev = STDEV(Close, period)`
- `upper_band = middle_band + (std_dev × std_dev_multiplier)`
- `lower_band = middle_band - (std_dev × std_dev_multiplier)`

**Relationships**:
- Calculated from `StockData.Close` prices
- Consumed by `SqueezeEvent` for detection
- Logged in `Trade` records for audit trail

**Implementation Notes**:
```python
from enum import Enum

class SqueezeStatus(str, Enum):
    NONE = "none"
    ACTIVE = "active"         # Band width decreasing by threshold
    EXPANDING = "expanding"   # Band width increasing after squeeze

@dataclass
class BollingerBand:
    stock_code: str
    calculation_date: datetime
    middle_band: Decimal
    upper_band: Decimal
    lower_band: Decimal
    band_width: Decimal
    period: int
    std_dev_multiplier: Decimal
    squeeze_status: SqueezeStatus = SqueezeStatus.NONE

    def __post_init__(self):
        """Validate band relationships"""
        if not (self.lower_band <= self.middle_band <= self.upper_band):
            raise ValueError("Band ordering violated: lower <= middle <= upper")
        if abs(self.band_width - (self.upper_band - self.lower_band)) > Decimal('0.01'):
            raise ValueError("Band width calculation inconsistent")

    @classmethod
    def from_price_series(cls, stock_code: str, date: datetime, prices: pd.Series,
                          period: int, std_dev_multiplier: float) -> 'BollingerBand':
        """Calculate Bollinger Bands using pandas-ta"""
        import pandas_ta as ta

        # Calculate using pandas-ta
        bb = prices.ta.bbands(length=period, std=std_dev_multiplier)
        latest = bb.iloc[-1]  # Get values for `date`

        return cls(
            stock_code=stock_code,
            calculation_date=date,
            middle_band=Decimal(str(latest[f'BBM_{period}_{std_dev_multiplier}'])),
            upper_band=Decimal(str(latest[f'BBU_{period}_{std_dev_multiplier}'])),
            lower_band=Decimal(str(latest[f'BBL_{period}_{std_dev_multiplier}'])),
            band_width=Decimal(str(latest[f'BBB_{period}_{std_dev_multiplier}'])),  # Bandwidth column
            period=period,
            std_dev_multiplier=Decimal(str(std_dev_multiplier))
        )
```

**Storage**:
- In-memory during backtest (computed on-demand from StockData)
- Logged as JSON metadata in Trade records
- Can be cached in DataFrame for visualization

---

## Entity 6: SqueezeEvent

**Purpose**: Represents a detected Bollinger Band squeeze (volatility contraction). Critical for signal generation in the squeeze strategy.

**Attributes**:
- `event_id` (UUID): Unique identifier
- `stock_code` (str): 6-digit stock code
- `detection_date` (datetime): When squeeze was first detected
- `band_width_at_detection` (Decimal): Current band width when squeeze triggered
- `band_width_N_days_ago` (Decimal): Band width at lookback start (e.g., 10 days ago)
- `width_decrease_pct` (Decimal): Percentage decrease (e.g., 30%)
- `lookback_days` (int): Comparison window (e.g., 10)
- `threshold_pct` (Decimal): Configured threshold (e.g., 30%)
- `direction_bias` (Enum): BULLISH (lower band touched), BEARISH (upper band touched), NEUTRAL
- `expansion_confirmed_date` (datetime | None): When bands started expanding again (signal trigger)

**Invariants**:
- `width_decrease_pct >= threshold_pct` (otherwise not a squeeze)
- `width_decrease_pct = ((band_width_N_days_ago - band_width_at_detection) / band_width_N_days_ago) * 100`

**Relationships**:
- Detected from `BollingerBand` history (10-day rolling window)
- Generates buy/sell signals when `expansion_confirmed_date` is set
- References `StockData` to determine direction_bias (which band price touched)

**Implementation Notes**:
```python
from enum import Enum

class DirectionBias(str, Enum):
    BULLISH = "bullish"    # Price touched lower band during squeeze
    BEARISH = "bearish"    # Price touched upper band during squeeze
    NEUTRAL = "neutral"    # No clear band touch

@dataclass
class SqueezeEvent:
    event_id: UUID
    stock_code: str
    detection_date: datetime
    band_width_at_detection: Decimal
    band_width_N_days_ago: Decimal
    width_decrease_pct: Decimal
    lookback_days: int
    threshold_pct: Decimal
    direction_bias: DirectionBias
    expansion_confirmed_date: Optional[datetime] = None

    def __post_init__(self):
        """Validate squeeze calculation"""
        expected_decrease = ((self.band_width_N_days_ago - self.band_width_at_detection) /
                             self.band_width_N_days_ago) * 100
        if abs(expected_decrease - self.width_decrease_pct) > Decimal('0.01'):
            raise ValueError("Width decrease percentage calculation inconsistent")
        if self.width_decrease_pct < self.threshold_pct:
            raise ValueError(f"Squeeze not met: {self.width_decrease_pct}% < {self.threshold_pct}%")

    def confirm_expansion(self, date: datetime):
        """Mark squeeze as resolved (bands expanding)"""
        if self.expansion_confirmed_date is not None:
            raise ValueError("Expansion already confirmed")
        self.expansion_confirmed_date = date

    def is_ready_for_signal(self) -> bool:
        """Check if squeeze can generate a trade signal"""
        return self.expansion_confirmed_date is not None
```

**Storage**:
- SQLite `squeeze_events` table
- JSON export for analysis
- Used for generating summary statistics (e.g., "15 squeeze events detected")

---

## Entity 7: BacktestConfiguration

**Purpose**: Represents all user-defined strategy parameters. Loaded from YAML file, validated via Pydantic.

**Attributes**:
- `seed_money` (int): Initial capital (KRW)
- `stocks` (List[str]): List of 6-digit stock codes to backtest
- `date_range` (Tuple[date, date]): Backtest period (start, end)
- `bollinger_period` (int): Moving average window (default 20)
- `bollinger_std_dev` (float): Standard deviation multiplier (default 2.0)
- `squeeze_threshold_percent` (float): Band width decrease threshold (default 30%)
- `squeeze_lookback_days` (int): Comparison window (default 10 days)
- `stop_loss_percent` (float): Maximum loss per position (default 5%)
- `max_position_size_percent` (float): Max allocation per stock (default 30%)
- `initial_positions` (Dict[str, Dict]): Existing positions at start (stock_code → {quantity, purchase_price})
- `risk_free_rate` (float): For Sharpe ratio calculation (default 3%)
- `transaction_cost_percent` (float): Commission/slippage (default 0%)

**Validation Rules** (from FR-045):
- `seed_money > 0`
- All `stocks` match `^\d{6}$`
- `5 <= bollinger_period <= 200`
- `0 < bollinger_std_dev <= 5`
- `5 <= squeeze_threshold_percent <= 100`
- `2 <= squeeze_lookback_days <= 30`
- `0 <= stop_loss_percent <= 100`
- `0 < max_position_size_percent <= 100`

**Implementation Notes**:
```python
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Tuple
from datetime import date

class BacktestConfiguration(BaseModel):
    seed_money: int = Field(gt=0, description="Initial capital (KRW)")
    stocks: List[str] = Field(min_length=1, description="Stock codes")
    date_range: Tuple[date, date]

    bollinger_period: int = Field(ge=5, le=200, default=20)
    bollinger_std_dev: float = Field(gt=0, le=5, default=2.0)

    squeeze_threshold_percent: float = Field(ge=5, le=100, default=30)
    squeeze_lookback_days: int = Field(ge=2, le=30, default=10)

    stop_loss_percent: float = Field(ge=0, le=100, default=5)
    max_position_size_percent: float = Field(gt=0, le=100, default=30)

    initial_positions: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    risk_free_rate: float = Field(default=0.03)  # 3% annualized
    transaction_cost_percent: float = Field(ge=0, default=0.0)

    @field_validator('stocks')
    def validate_stock_codes(cls, v):
        for code in v:
            if not (code.isdigit() and len(code) == 6):
                raise ValueError(f"Invalid stock code: {code} (must be 6 digits)")
        return v

    @field_validator('date_range')
    def validate_date_range(cls, v):
        start, end = v
        if start >= end:
            raise ValueError(f"Start date must be before end date: {start} >= {end}")
        return v

    @classmethod
    def from_yaml(cls, path: str) -> 'BacktestConfiguration':
        """Load configuration from YAML file"""
        import yaml
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls(**data)
```

**Storage**:
- YAML files in `config/` directory
- Example: `config/default.yaml`, `config/examples/multi_stock.yaml`

---

## Entity 8: PerformanceReport

**Purpose**: Represents the outcome of a backtest. Aggregates all performance metrics, trade history, and equity curve.

**Attributes**:
- `report_id` (UUID): Unique identifier
- `config` (BacktestConfiguration): Configuration used for this backtest
- `backtest_date` (datetime): When backtest was run
- `final_portfolio_value` (Decimal): Ending total value
- `total_return_pct` (Decimal): ((final - initial) / initial) × 100
- `win_rate_pct` (Decimal): (winning_trades / total_trades) × 100
- `max_drawdown_pct` (Decimal): Largest peak-to-trough decline
- `sharpe_ratio` (Decimal): Risk-adjusted return metric
- `num_trades` (int): Total trades executed
- `num_squeeze_events` (int): Total squeeze events detected
- `trade_history` (List[Trade]): All executed trades
- `squeeze_log` (List[SqueezeEvent]): All detected squeezes
- `equity_curve` (DataFrame): Timestamp-indexed portfolio value history

**Computed Metrics** (from SC-005):
- `total_return_pct = ((final_portfolio_value - initial_capital) / initial_capital) × 100`
- `win_rate_pct = (num_winning_trades / num_trades) × 100` where winning_trades = trades with realized_pnl > 0
- `max_drawdown_pct = max((peak - trough) / peak)` for all peak-to-trough sequences
- `sharpe_ratio = (avg_return - risk_free_rate) / std_dev_returns` (annualized)

**Relationships**:
- Generated from `Portfolio` final state
- Contains all `Trade` records
- Contains all `SqueezeEvent` records
- Uses `QuantStats` for metric calculation

**Implementation Notes**:
```python
@dataclass
class PerformanceReport:
    report_id: UUID
    config: BacktestConfiguration
    backtest_date: datetime
    final_portfolio_value: Decimal
    total_return_pct: Decimal
    win_rate_pct: Decimal
    max_drawdown_pct: Decimal
    sharpe_ratio: Decimal
    num_trades: int
    num_squeeze_events: int
    trade_history: List[Trade]
    squeeze_log: List[SqueezeEvent]
    equity_curve: pd.DataFrame

    @classmethod
    def from_backtest(cls, portfolio: Portfolio, trades: List[Trade],
                      squeezes: List[SqueezeEvent], config: BacktestConfiguration) -> 'PerformanceReport':
        """Generate report from backtest results"""
        import quantstats as qs

        # Calculate metrics
        initial = config.seed_money
        final = portfolio.total_value
        total_return = ((final - initial) / initial) * 100

        winning_trades = [t for t in trades if t.realized_pnl and t.realized_pnl > 0]
        win_rate = (len(winning_trades) / len(trades)) * 100 if trades else 0

        # Convert equity curve to returns for QuantStats
        equity_df = pd.DataFrame(portfolio.equity_curve, columns=['date', 'value'])
        equity_df.set_index('date', inplace=True)
        returns = equity_df['value'].pct_change().dropna()

        mdd = qs.stats.max_drawdown(returns) * 100  # Convert to percentage
        sharpe = qs.stats.sharpe(returns, rf=config.risk_free_rate)

        return cls(
            report_id=uuid4(),
            config=config,
            backtest_date=datetime.now(),
            final_portfolio_value=final,
            total_return_pct=Decimal(str(total_return)),
            win_rate_pct=Decimal(str(win_rate)),
            max_drawdown_pct=Decimal(str(mdd)),
            sharpe_ratio=Decimal(str(sharpe)),
            num_trades=len(trades),
            num_squeeze_events=len(squeezes),
            trade_history=trades,
            squeeze_log=squeezes,
            equity_curve=equity_df
        )

    def export_to_dict(self) -> Dict:
        """Export metrics for JSON serialization"""
        return {
            "report_id": str(self.report_id),
            "backtest_date": self.backtest_date.isoformat(),
            "final_portfolio_value": float(self.final_portfolio_value),
            "total_return_pct": float(self.total_return_pct),
            "win_rate_pct": float(self.win_rate_pct),
            "max_drawdown_pct": float(self.max_drawdown_pct),
            "sharpe_ratio": float(self.sharpe_ratio),
            "num_trades": self.num_trades,
            "num_squeeze_events": self.num_squeeze_events,
            "trades": [t.to_log_dict() for t in self.trade_history]
        }
```

**Storage**:
- JSON: `data/logs/report_{report_id}.json`
- CSV: `data/logs/trades_{report_id}.csv`, `data/logs/equity_{report_id}.csv`
- SQLite: `backtest_results` table with summary metrics

---

## Entity Relationships Diagram

```
┌──────────────────────┐
│ BacktestConfiguration│
│ (YAML config)        │
└──────────┬───────────┘
           │ configures
           ▼
┌──────────────────────┐      contains      ┌─────────────┐
│     Portfolio        │◄────────────────────┤  Position   │
│  - cash_balance      │                     │ - stock_code│
│  - total_value       │                     │ - quantity  │
│  - equity_curve      │                     │ - pnl       │
└──────────┬───────────┘                     └─────┬───────┘
           │ generates                             │ uses
           │                                       │
           ▼                                       ▼
     ┌─────────┐                            ┌────────────┐
     │  Trade  │                            │ StockData  │
     │ (audit) │                            │  (OHLCV)   │
     └─────┬───┘                            └─────┬──────┘
           │ references                           │
           │                                      │ input to
           ▼                                      ▼
  ┌────────────────┐                      ┌─────────────────┐
  │ BollingerBand  │──────calculates──────┤  band_width     │
  │ - upper/middle │                      │                 │
  │ - lower/width  │                      └─────┬───────────┘
  └────────┬───────┘                            │ used by
           │ feeds into                         │
           ▼                                    ▼
    ┌──────────────┐                     ┌──────────────┐
    │ SqueezeEvent │─────triggers────────► SignalGen    │
    │ - direction  │                     │ (buy/sell)   │
    │ - expansion  │                     └──────────────┘
    └──────────────┘
           │
           │ aggregated in
           ▼
  ┌──────────────────┐
  │ PerformanceReport│
  │ - metrics        │
  │ - trade history  │
  └──────────────────┘
```

---

## Data Validation Summary

Per Constitutional Principle VII (Defensive Validation):

| Entity | Validation Method | Failure Behavior |
|--------|-------------------|------------------|
| Portfolio | `cash_balance >= 0` check | Raise ValueError, halt execution |
| Position | Pydantic validators, `__post_init__` checks | Raise ValueError on creation |
| Trade | Immutable dataclass, `__post_init__` validation | Raise ValueError if inconsistent |
| StockData | OHLCV relationship checks, outlier detection | Raise ValueError, flag outliers |
| BollingerBand | Band ordering invariants | Raise ValueError if violated |
| SqueezeEvent | Width decrease calculation validation | Raise ValueError if threshold not met |
| BacktestConfiguration | Pydantic field validators | Raise ValidationError with clear message |
| PerformanceReport | QuantStats library (validated) | N/A (computed from validated inputs) |

All validations fail-fast with structured error messages per constitutional requirements.
