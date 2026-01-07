# Quickstart: Advanced Sell Strategy

**Feature**: 006-advanced-sell-strategy  
**Date**: 2026-01-07

## Prerequisites

- Python 3.11+
- Running PostgreSQL/SQLite database
- Existing positions in portfolio

## Implementation Steps

### Step 1: Database Migration

Add `partial_take_profit_executed` field to Position model:

```bash
cd trading_wizard_web/backend
alembic revision --autogenerate -m "add partial_take_profit_executed to positions"
alembic upgrade head
```

### Step 2: Update Position Model

File: `trading_wizard_web/backend/src/models/position.py`

Add new column:
```python
partial_take_profit_executed = Column(Boolean, nullable=False, default=False)
```

Add method to mark take-profit executed:
```python
def mark_take_profit_executed(self):
    self.partial_take_profit_executed = True
```

### Step 3: Update SignalScanner

File: `trading_wizard_web/backend/src/wizard/signal_scanner.py`

1. Add new parameters to `__init__`:
   - `take_profit_pct: float = 10.0`
   - `take_profit_ratio: float = 0.5`

2. Modify `scan_for_sell_signals()` to implement priority-based evaluation:
   - Priority 1: Stop-loss check (existing)
   - Priority 2: Take-profit check (new)
   - Priority 3: Trend breakdown - middle band (replaces lower band)

3. Add `sell_quantity` and `sell_ratio` to signal indicators dict

### Step 4: Update Tests

File: `trading_wizard_web/backend/tests/unit/test_sell_strategy.py`

Test cases to add:
- Stop-loss triggers at -5% (existing behavior)
- Take-profit triggers at +10% with 50% sell
- Take-profit does not re-trigger after execution
- Trend breakdown triggers when close < middle band
- Priority order is respected
- Minimum share handling (round up to 1)

### Step 5: Verification

Run test suite:
```bash
cd trading_wizard_web/backend
pytest tests/unit/test_sell_strategy.py -v
```

Manual verification:
1. Create test position with known entry price
2. Simulate price scenarios:
   - Drop to -5% → expect stop-loss signal
   - Rise to +10% → expect partial take-profit signal
   - Drop below middle band → expect trend breakdown signal

## Configuration

Default values (can be overridden in SignalScanner initialization):

| Parameter | Default | Description |
|-----------|---------|-------------|
| stop_loss_percent | 5.0 | Stop-loss trigger threshold |
| take_profit_pct | 10.0 | Take-profit trigger threshold |
| take_profit_ratio | 0.5 | Portion of position to sell on take-profit |

## Key Files Modified

| File | Change |
|------|--------|
| `models/position.py` | Add `partial_take_profit_executed` column |
| `wizard/signal_scanner.py` | Modify `scan_for_sell_signals()` logic |
| `alembic/versions/*.py` | New migration for database schema |
| `tests/unit/test_sell_strategy.py` | New test file |

## Rollback

If needed, rollback database migration:
```bash
alembic downgrade -1
```

Remove the `partial_take_profit_executed` column from Position model and revert SignalScanner changes.
