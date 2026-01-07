# Research: Advanced Sell Strategy

**Feature**: 006-advanced-sell-strategy  
**Date**: 2026-01-07

## Research Tasks

### 1. Existing Sell Logic Analysis

**Task**: Analyze current `scan_for_sell_signals()` implementation to understand modification points.

**Findings**:
- Located in `trading_wizard_web/backend/src/wizard/signal_scanner.py` (lines 366-430)
- Current conditions:
  1. Stop-loss: `pnl_pct <= -self.stop_loss_percent` → full sell
  2. Lower band touch: `current_price < latest["BB_Lower"]` → full sell
- Returns `List[StockSignal]` with reason strings
- Position data comes from dict with keys: `stock_code`, `avg_entry_price`, `quantity`

**Decision**: Modify in-place. Replace lower band condition with middle band; add take-profit check between stop-loss and trend-breakdown.

### 2. Position State Persistence

**Task**: Determine how to track `partial_take_profit_executed` persistently.

**Findings**:
- Position model in `trading_wizard_web/backend/src/models/position.py`
- Uses SQLAlchemy ORM with PostgreSQL/SQLite
- Existing fields: `stock_code`, `quantity`, `avg_entry_price`, `first_entry_date`, `entry_reason`, `confidence_score`
- Alembic migrations in `trading_wizard_web/backend/alembic/versions/`

**Decision**: Add `partial_take_profit_executed` boolean field to Position model with Alembic migration. Default `False`. Set to `True` when partial take-profit signal is generated.

**Rationale**: Database persistence ensures state survives app restarts (addresses Edge Case in spec).

**Alternatives Considered**:
- In-memory tracking: Rejected - lost on restart
- Separate tracking table: Rejected - over-engineering for single boolean

### 3. Sell Signal Output Enhancement

**Task**: Determine how to include sell quantity in signal output.

**Findings**:
- Current `StockSignal` dataclass has: `stock_code`, `stock_name`, `signal_type`, `confidence_score`, `current_price`, `reason`, `indicators`
- No quantity field exists
- `indicators` dict is used for additional data (entry_price, pnl_pct, bb_lower, etc.)

**Decision**: Add `sell_quantity` and `sell_ratio` to `indicators` dict for backward compatibility. No schema change to StockSignal.

**Rationale**: Minimizes breaking changes; consuming code can optionally use new fields.

**Alternatives Considered**:
- New fields on StockSignal: Would require updating all consumers
- Separate SellSignal class: Over-engineering; StockSignal with signal_type="SELL" is sufficient

### 4. Priority Evaluation Order

**Task**: Confirm priority order implementation approach.

**Findings**:
- Spec requires: (1) Stop-Loss, (2) Take-Profit, (3) Trend-Breakdown
- Current code uses if-elif structure
- Take-profit is partial (50%), others are full (100%)
- Same position could trigger both take-profit AND trend-breakdown in one scan (take-profit for 50%, then trend-breakdown for remaining 50%)

**Decision**: Implement as sequential checks with early return for stop-loss. Take-profit and trend-breakdown can coexist if take-profit is first-time and trend-breakdown condition also met.

**Rationale**: Acceptance Scenario 4 in User Story 3 explicitly requires this behavior.

### 5. Minimum Share Calculation

**Task**: Determine rounding behavior for partial take-profit.

**Findings**:
- Clarification session resolved: "Sell minimum 1 share (round up)"
- Python `math.ceil()` provides ceiling function
- Edge case: 1 share position with 50% ratio = ceil(0.5) = 1 share

**Decision**: Use `max(1, math.ceil(quantity * take_profit_ratio))` for sell quantity calculation.

**Rationale**: Ensures take-profit always executes per clarified requirement.

### 6. Configuration Integration

**Task**: Determine how sell parameters are configured.

**Findings**:
- Current `SignalScanner.__init__()` accepts `stop_loss_percent` (default 5.0)
- No take-profit parameters exist yet
- User settings stored in `user_settings` table via `settings_service.py`

**Decision**: Add `sell_take_profit_pct` (default 10.0) and `sell_take_profit_ratio` (default 0.5) as SignalScanner init parameters. Follow existing pattern.

**Rationale**: Consistent with existing architecture; allows per-scan configuration.

## Summary

| Item | Decision | Impact |
|------|----------|--------|
| Sell logic location | Modify `signal_scanner.py` in-place | Low risk |
| Take-profit tracking | New boolean field on Position model | DB migration required |
| Signal output | Extend `indicators` dict | Backward compatible |
| Priority order | Sequential if-elif with coexistence | Logic change |
| Minimum shares | `max(1, ceil(qty * ratio))` | Edge case handling |
| Configuration | New SignalScanner init params | API change |

## Open Items

None - all research tasks resolved.
