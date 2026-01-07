# Data Model: Advanced Sell Strategy

**Feature**: 006-advanced-sell-strategy  
**Date**: 2026-01-07

## Entity Changes

### Position (Modified)

**Location**: `trading_wizard_web/backend/src/models/position.py`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| id | UUID | Yes | auto | Primary key (existing) |
| portfolio_id | UUID | Yes | - | Foreign key to Portfolio (existing) |
| stock_code | String(6) | Yes | - | Stock code e.g., "005930" (existing) |
| stock_name | String(100) | Yes | - | Stock name (existing) |
| quantity | Integer | Yes | - | Number of shares held (existing) |
| avg_entry_price | Decimal(12,2) | Yes | - | Average purchase price (existing) |
| first_entry_date | Date | Yes | - | First purchase date (existing) |
| entry_reason | String(50) | No | null | Buy signal reason (existing) |
| confidence_score | Integer | No | null | Buy confidence 0-100 (existing) |
| **partial_take_profit_executed** | **Boolean** | **Yes** | **False** | **NEW: Whether partial TP has fired** |
| updated_at | DateTime | Yes | now() | Last update timestamp (existing) |

**Migration Required**: Yes - Alembic migration to add `partial_take_profit_executed` column with default `False`.

### SellSignal (Output Structure)

**Location**: Part of `StockSignal` dataclass in `trading_wizard_web/backend/src/wizard/signal_scanner.py`

No schema change to `StockSignal`. Sell-specific data in `indicators` dict:

| Field in `indicators` | Type | Description |
|----------------------|------|-------------|
| entry_price | float | Position entry price |
| pnl_pct | float | Current P&L percentage |
| bb_lower | float | Bollinger lower band |
| bb_middle | float | Bollinger middle band (20 MA) |
| bb_upper | float | Bollinger upper band |
| rsi | float | RSI value |
| **sell_quantity** | **int** | **NEW: Number of shares to sell** |
| **sell_ratio** | **float** | **NEW: Percentage of position to sell (0.0-1.0)** |

### SellConfiguration (New Concept)

**Location**: Parameters in `SignalScanner.__init__()`

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| stop_loss_percent | float | 5.0 | 1.0-20.0 | Stop-loss threshold (existing) |
| **take_profit_pct** | **float** | **10.0** | **5.0-50.0** | **NEW: Take-profit threshold** |
| **take_profit_ratio** | **float** | **0.5** | **0.1-1.0** | **NEW: Partial sell ratio** |

## State Transitions

### Position Lifecycle with Sell Strategy

```
[Created] ──buy──> [Active]
                      │
                      ├── stop_loss_hit ───────────────> [Closed/Removed]
                      │   (pnl <= -stop_loss_pct)
                      │   sell 100%
                      │
                      ├── take_profit_target_hit ──────> [Active, TP Executed]
                      │   (pnl >= +take_profit_pct        partial_take_profit_executed = True
                      │    AND !partial_take_profit_executed)
                      │   sell take_profit_ratio (default 50%)
                      │
                      └── trend_broken_middle_band ────> [Closed/Removed]
                          (close < bb_middle)
                          sell 100% of remaining

[Active, TP Executed] ─┬─ stop_loss_hit ──────────────> [Closed/Removed]
                       │
                       └─ trend_broken_middle_band ───> [Closed/Removed]
```

### Sell Signal Priority Flow

```
For each position:
  1. Calculate PnL% = (current_price - entry_price) / entry_price * 100
  
  2. IF pnl <= -stop_loss_pct:
       → SELL 100%, reason="stop_loss_hit"
       → RETURN (no further checks)
  
  3. IF pnl >= +take_profit_pct AND NOT partial_take_profit_executed:
       → SELL take_profit_ratio%, reason="take_profit_target_hit"
       → Mark position.partial_take_profit_executed = True
       → CONTINUE (check trend breakdown for remaining)
  
  4. IF current_price < bb_middle:
       → SELL 100% of remaining, reason="trend_broken_middle_band"
       → RETURN
  
  5. No signal
```

## Validation Rules

| Entity | Rule | Error |
|--------|------|-------|
| Position | quantity >= 0 | "Invalid quantity" |
| Position | sell_quantity <= quantity | "Cannot sell more than owned" |
| SellConfiguration | stop_loss_percent in [1.0, 20.0] | "Stop-loss out of range" |
| SellConfiguration | take_profit_pct in [5.0, 50.0] | "Take-profit out of range" |
| SellConfiguration | take_profit_ratio in [0.1, 1.0] | "Take-profit ratio out of range" |

## Database Migration

**File**: `alembic/versions/XXX_add_partial_take_profit_executed.py`

```python
# Migration summary (actual file generated during implementation)
def upgrade():
    op.add_column('positions', 
        sa.Column('partial_take_profit_executed', sa.Boolean(), 
                  nullable=False, server_default='false'))

def downgrade():
    op.drop_column('positions', 'partial_take_profit_executed')
```
