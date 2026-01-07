# Implementation Plan: Advanced Sell Strategy

**Branch**: `006-advanced-sell-strategy` | **Date**: 2026-01-07 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-advanced-sell-strategy/spec.md`

## Summary

Improve the existing sell logic in `SignalScanner.scan_for_sell_signals()` to implement a priority-based sell strategy with three conditions: stop-loss (existing, -5%), partial take-profit (new, +10% triggers 50% sell), and trend breakdown (new, close < middle band replaces lower band touch). Requires adding `partial_take_profit_executed` tracking to Position model and extending SellSignal output with quantity information.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: pandas, yfinance, SQLAlchemy, FastAPI  
**Storage**: SQLite/PostgreSQL via SQLAlchemy ORM, JSON files for portfolio state  
**Testing**: pytest (unit/integration/contract tests)  
**Target Platform**: Web application (Linux server / Docker)  
**Project Type**: Web application (backend + frontend)  
**Performance Goals**: Sell signal generation within 1 second per position (SC-001)  
**Constraints**: Must maintain existing stop-loss behavior; partial take-profit executes once per position lifecycle  
**Scale/Scope**: ~100 stocks in universe, ~15 max concurrent positions per portfolio

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Requirement | Status | Notes |
|-----------|-------------|--------|-------|
| **I. Data-Driven Strategy** | Strategy changes backed by quantitative data | PASS | Sell strategy thresholds (5% SL, 10% TP) are configurable and testable via backtest |
| **II. Simplicity Over Complexity** | Complexity only with clear improvement | PASS | Middle band exit simplifies from lower band (earlier exit); partial TP adds value without over-engineering |
| **III. Risk Management First** | Stop-loss (-5%) must be maintained | PASS | FR-001 specifies stop-loss has highest priority; FR-002 maintains -5% default |
| **III. Risk Management First** | Max 15 positions | N/A | Not affected by this feature |
| **III. Risk Management First** | Max 10% per position | N/A | Not affected by this feature |
| **IV. Reproducibility** | All trades recorded with reason | PASS | FR-007 specifies reason strings; FR-008 includes quantity in output |
| **V. User Transparency** | Show trading rationale | PASS | Sell signals include reason, PnL%, and quantity |

**Gate Status**: PASS - All applicable principles satisfied

## Project Structure

### Documentation (this feature)

```text
specs/006-advanced-sell-strategy/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── sell-signal-api.yaml
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
trading_wizard_web/
├── backend/
│   ├── src/
│   │   ├── models/
│   │   │   └── position.py          # Add partial_take_profit_executed field
│   │   ├── wizard/
│   │   │   └── signal_scanner.py    # Modify scan_for_sell_signals()
│   │   └── api/
│   │       └── recommendations.py   # Update response schema
│   ├── alembic/
│   │   └── versions/                # Migration for new field
│   └── tests/
│       ├── unit/
│       │   └── test_sell_strategy.py
│       └── integration/
│           └── test_sell_signals.py
└── frontend/
    └── [no changes required for this feature]
```

**Structure Decision**: Web application structure. Changes are backend-only, focused on `wizard/signal_scanner.py` for core logic and `models/position.py` for state tracking.

## Complexity Tracking

> No violations - all changes align with Constitution principles.

| Aspect | Justification |
|--------|---------------|
| New DB field | `partial_take_profit_executed` is minimal addition to existing Position model |
| Priority evaluation | Simple if-elif chain, no complex state machine |
| Middle band exit | Simpler than previous lower band (same indicator, different threshold) |
