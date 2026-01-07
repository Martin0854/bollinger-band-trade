# Feature Specification: Advanced Sell Strategy

**Feature Branch**: `006-advanced-sell-strategy`  
**Created**: 2026-01-07  
**Status**: Draft  
**Input**: Improve sell logic with stop-loss, partial take-profit, and middle band trend breakdown

## Clarifications

### Session 2026-01-07

- Q: For minimum position sizes during partial take-profit (ratio yields < 1 share), should system sell minimum 1 share or skip? → A: Sell minimum 1 share (round up)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Stop Loss Protection (Priority: P1)

As a trader with existing positions, I want the system to automatically trigger a full exit when my position drops to -5% or below, so that I can limit my losses and protect my capital.

**Why this priority**: This is the most critical risk management feature. Without proper stop-loss, a single bad trade can wipe out multiple winning trades. This must work reliably before any other sell logic.

**Independent Test**: Can be fully tested by creating a position and simulating a price drop of 5% or more. Delivers immediate capital protection value.

**Acceptance Scenarios**:

1. **Given** a position with entry price 10,000 KRW and `sell_stop_loss_pct` set to 5.0%, **When** current price drops to 9,500 KRW (exactly -5%), **Then** system generates a SELL signal for 100% of position with reason "stop_loss_hit"
2. **Given** a position with entry price 10,000 KRW, **When** current price is 9,600 KRW (-4%), **Then** system does NOT generate a stop-loss sell signal
3. **Given** a position with entry price 10,000 KRW, **When** current price drops to 9,000 KRW (-10%), **Then** system generates a SELL signal for 100% of position with reason "stop_loss_hit" (stop-loss takes priority over other conditions)

---

### User Story 2 - Partial Take Profit (Priority: P2)

As a trader with a profitable position, I want the system to automatically sell 50% of my position when gains reach +10% or more, so that I can lock in profits while maintaining upside potential.

**Why this priority**: After ensuring loss protection (P1), securing partial profits is the next most valuable feature. It reduces risk by recovering initial capital while allowing remaining position to ride further gains.

**Independent Test**: Can be fully tested by creating a position and simulating a 10%+ price increase. Delivers profit-locking value independent of other sell conditions.

**Acceptance Scenarios**:

1. **Given** a position of 100 shares with entry price 10,000 KRW and `sell_take_profit_pct` set to 10.0%, **When** current price reaches 11,000 KRW (+10%), **Then** system generates a SELL signal for 50 shares (50%) with reason "take_profit_target_hit"
2. **Given** a position of 100 shares with entry price 10,000 KRW, **When** current price is 10,900 KRW (+9%), **Then** system does NOT generate a take-profit sell signal
3. **Given** a position where partial take-profit has already been executed, **When** price remains above +10%, **Then** system does NOT generate another take-profit signal (only one partial take-profit per position)
4. **Given** a position of 100 shares with `sell_take_profit_ratio` set to 0.3 (30%), **When** take-profit condition is met, **Then** system generates a SELL signal for 30 shares

---

### User Story 3 - Trend Breakdown Exit (Priority: P3)

As a trader holding a position, I want the system to exit my remaining position when the closing price falls below the 20-day moving average (Bollinger middle band), so that I can exit before larger losses occur during trend reversals.

**Why this priority**: This replaces the old "lower band touch" logic which triggered too late. Middle band breakdown provides earlier exit signal to minimize profit give-back during downtrends. Depends on P1/P2 to be meaningful.

**Independent Test**: Can be fully tested by creating a position and simulating price crossing below the middle band. Delivers trend-following exit value.

**Acceptance Scenarios**:

1. **Given** a position with remaining shares after partial take-profit, **When** closing price drops below Bollinger middle band (20 MA), **Then** system generates a SELL signal for 100% of remaining position with reason "trend_broken_middle_band"
2. **Given** a position where stop-loss has NOT been triggered, **When** closing price is above middle band, **Then** system does NOT generate a trend-breakdown sell signal
3. **Given** a position, **When** closing price drops below middle band BUT stop-loss condition is also met, **Then** system generates stop-loss signal (higher priority) NOT trend-breakdown signal
4. **Given** a position, **When** closing price drops below middle band BUT take-profit condition is also met (first time), **Then** system generates take-profit signal (higher priority) first, then trend-breakdown for remaining shares

---

### User Story 4 - Configurable Sell Parameters (Priority: P3)

As a trader, I want to customize the sell strategy parameters (stop-loss %, take-profit %, take-profit ratio), so that I can adapt the strategy to my risk tolerance and market conditions.

**Why this priority**: Configuration flexibility is important for personalization but the core logic (P1-P3) must work with defaults first. This is enhancement on top of working functionality.

**Independent Test**: Can be fully tested by changing configuration values and verifying that sell signals respect new thresholds. Delivers customization value.

**Acceptance Scenarios**:

1. **Given** `sell_stop_loss_pct` is set to 3.0%, **When** position drops to -3%, **Then** stop-loss triggers at the new threshold
2. **Given** `sell_take_profit_pct` is set to 15.0%, **When** position gains +10%, **Then** take-profit does NOT trigger (needs +15%)
3. **Given** `sell_take_profit_ratio` is set to 0.7, **When** take-profit triggers, **Then** 70% of position is sold instead of 50%

---

### Edge Cases

- What happens when a position has only 1 share and take-profit triggers 50%? System sells minimum 1 share (round up), ensuring take-profit always executes regardless of position size.
- What happens when take-profit was already executed but quantity tracking is lost (e.g., app restart)? System needs persistent state to track whether partial take-profit has been executed per position.
- What happens when all three sell conditions are met simultaneously? System evaluates in priority order: stop-loss first, then take-profit, then trend-breakdown.
- What happens when price gaps down significantly (e.g., -15% overnight)? Stop-loss still triggers at actual loss percentage, even if greater than threshold.
- What happens when middle band value is NaN (insufficient data)? Trend-breakdown check is skipped; only stop-loss and take-profit are evaluated.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST evaluate sell conditions in strict priority order: (1) Stop-Loss, (2) Take-Profit, (3) Trend-Breakdown
- **FR-002**: System MUST generate a 100% exit signal when position PnL <= negative stop-loss threshold (default -5%)
- **FR-003**: System MUST generate a partial exit signal (default 50%) when position PnL >= take-profit threshold (default +10%) AND partial take-profit has not been executed for this position
- **FR-004**: System MUST generate a 100% exit signal for remaining position when closing price < Bollinger middle band (20 MA)
- **FR-005**: System MUST track whether partial take-profit has been executed for each position
- **FR-006**: System MUST allow configuration of `sell_stop_loss_pct` (default 5.0), `sell_take_profit_pct` (default 10.0), and `sell_take_profit_ratio` (default 0.5)
- **FR-007**: System MUST return appropriate sell reason strings: "stop_loss_hit", "take_profit_target_hit", "trend_broken_middle_band"
- **FR-008**: System MUST include sell quantity (shares or percentage) in the sell signal output
- **FR-009**: System MUST NOT trigger take-profit more than once per position lifecycle
- **FR-010**: System MUST handle minimum position sizes - if take-profit ratio results in less than 1 share, sell minimum 1 share (round up)

### Key Entities

- **Position**: Represents a held stock position. Key attributes: stock_code, quantity, avg_entry_price, partial_take_profit_executed (boolean), entry_date
- **SellSignal**: Represents a sell recommendation. Key attributes: stock_code, signal_type, reason, sell_quantity (absolute shares), sell_ratio (percentage), current_price, pnl_percentage
- **SellConfiguration**: Holds sell strategy parameters. Key attributes: stop_loss_pct, take_profit_pct, take_profit_ratio

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All sell signals are generated within 1 second of data availability per position
- **SC-002**: 100% of positions hitting stop-loss threshold receive sell signals (no missed stop-losses)
- **SC-003**: Partial take-profit executes exactly once per position lifecycle with correct quantity calculation
- **SC-004**: Trend-breakdown exits occur before price drops an additional 5% below middle band (early exit vs. lower band)
- **SC-005**: Configuration changes take effect immediately on next signal scan without requiring system restart
- **SC-006**: All sell signals include complete information (reason, quantity, price, PnL) for trading execution
