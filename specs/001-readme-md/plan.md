# Implementation Plan: Bollinger Band Auto-Trading Bot

**Branch**: `001-readme-md` | **Date**: 2025-10-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-readme-md/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a backtesting system for Bollinger Band squeeze trading strategy on Korean stock market (KOSPI/KOSDAQ). The system detects volatility contractions (30% band width decrease over 10 days), generates entry signals on expansion based on prior band touch direction, and manages risk through stop-loss and position sizing controls. Primary technical approach: Python-based vectorized backtesting using vectorbt for performance (5-second target for 250 days), FinanceDataReader/pykrx for Korean market data, pandas-ta for indicators, and comprehensive test coverage via pytest following TDD principles.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: vectorbt 0.26+, FinanceDataReader 0.9+, pykrx 1.0+, pandas-ta 0.3+, numba 0.58+
**Storage**: Parquet (PyArrow 14+) for historical OHLCV data cache, SQLite for trade logs and backtest results
**Testing**: pytest 8.0+, pytest-benchmark, hypothesis (property-based testing for indicators)
**Target Platform**: Cross-platform (Linux/macOS/Windows), Python 3.11+ runtime
**Project Type**: Single (command-line backtesting tool)
**Performance Goals**: Process 250 trading days (1 year) in <5 seconds, indicator calculations <100ms, memory <500MB
**Constraints**: No lookahead bias in calculations, deterministic execution for reproducibility, sub-200ms total latency for real-time readiness
**Scale/Scope**: MVP supports 1-10 stocks per backtest, 1-5 year historical range, single portfolio account

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Data Integrity First ✅ PASS

**Compliance**:
- FR-003: Validates data completeness before backtesting
- FR-004: Outlier detection for anomalous price spikes
- FR-002: OHLCV data fetched with schema validation
- Data validation pipeline: FinanceDataReader → Pydantic schema validation → outlier detection → Parquet storage

**Implementation Approach**: Pydantic models validate all fetched data (positive prices, volume ranges, timestamp consistency). Outlier detection uses z-score analysis on daily returns (>3σ flagged). KRX timezone handling (Asia/Seoul) enforced via pandas DatetimeIndex.

### Principle II: Risk Management by Design ✅ PASS

**Compliance**:
- FR-008: Maximum position size configurable (default 30%)
- FR-009: Stop-loss threshold enforcement (default 5%)
- FR-010: Portfolio-level exposure caps
- FR-022: Stop-loss signals generated automatically
- FR-023: Stop-loss prioritized over squeeze signals

**Implementation Approach**: Risk controls implemented as portfolio constraints in vectorbt. Position sizing calculated as `min(cash / price, portfolio_value * max_position_pct / price)`. Stop-loss checked on every timestep, overrides all other signals when triggered.

### Principle III: Test-First Development (NON-NEGOTIABLE) ✅ PASS

**Compliance**:
- Committed to TDD workflow: write tests → stakeholder approval → verify failure → implement → verify pass
- Test coverage targets: Bollinger Band calculation (unit), squeeze detection (unit + property-based), signal generation (integration), end-to-end backtest scenarios (contract)
- Pytest + hypothesis for property-based testing (e.g., "band width always >= 0", "stop-loss triggers at exactly threshold%")
- pytest-benchmark for performance regression detection

**Implementation Approach**: All indicator calculations tested against reference implementations (pandas-ta). Hypothesis generates random OHLCV data to verify invariants (middle band always between upper/lower, squeeze detection symmetric). Integration tests validate full backtest scenarios from spec acceptance criteria.

### Principle IV: Backtesting Integrity ✅ PASS

**Compliance**:
- FR-014: No lookahead bias - calculations use only prior data
- FR-027: Trade execution at closing price (realistic timing)
- FR-031: Transaction costs initially zero (documented assumption), configurable for future
- Separate train/validation: Parameter optimization (FR-P4) uses walk-forward or separate test set

**Implementation Approach**: vectorbt's `from_signals` method ensures temporal ordering. Indicator calculations use `window=period` with `.shift(1)` to prevent lookahead. Backtest engine processes chronologically, state updates only after signal execution. Transaction costs modeled as `cost_pct` parameter in vectorbt Portfolio (initially 0%).

### Principle V: Transparency & Auditability ✅ PASS

**Compliance**:
- FR-038: Trade decision logging with Bollinger values, band width, signal type
- FR-039: Complete trade history with entry/exit prices, holding period, P/L
- FR-040: Portfolio state snapshots at each trade event
- FR-041: Export to CSV/JSON
- FR-042: Squeeze event logging (detection date, width decrease %, direction bias)

**Implementation Approach**: Structured logging using Python `logging` module with JSON formatter. Each trade logged as:
```json
{
  "timestamp": "2024-03-15T09:00:00+09:00",
  "stock_code": "005930",
  "action": "buy",
  "quantity": 50,
  "price": 60000,
  "reason": "squeeze_expansion_buy",
  "bollinger_upper": 65000,
  "bollinger_middle": 60000,
  "bollinger_lower": 55000,
  "band_width": 10000,
  "squeeze_status": "expanding",
  "portfolio_value_before": 10000000,
  "portfolio_value_after": 7000000,
  "cash_after": 7000000
}
```
Logs persisted to SQLite `trade_log` table for querying/analysis.

### Principle VI: Configuration Over Code ✅ PASS

**Compliance**:
- FR-043: YAML configuration file for all strategy parameters
- FR-044: Save/load multiple configuration presets
- FR-045: Validation of all config values

**Implementation Approach**: Pydantic `BaseSettings` class loads config from YAML:
```yaml
seed_money: 10000000
stocks: ["005930", "000660"]
bollinger_period: 20
bollinger_std_dev: 2.0
squeeze_threshold_percent: 30
squeeze_lookback_days: 10
stop_loss_percent: 5
max_position_size_percent: 30
initial_positions:
  "005930": {quantity: 10, purchase_price: 60000}
```
Validation via Pydantic constraints (`PositiveInt`, `confloat(gt=0, le=100)`). No code changes for parameter tuning - all strategy logic reads from config instance.

### Principle VII: Defensive Validation ✅ PASS

**Compliance**:
- FR-003: Data completeness checks before backtesting
- FR-004: Price/volume outlier detection
- FR-045: Configuration value validation (positive money, valid ranges)
- FR-032: Trade execution prevented if insufficient cash
- All API responses validated via Pydantic schemas

**Implementation Approach**:
- Market data: FinanceDataReader responses validated against OHLCV schema (positive prices, volume >= 0, valid dates)
- Configuration: Pydantic enforces constraints at load time, raises ValidationError with clear messages
- State transitions: Portfolio class validates `cash >= 0`, `quantity >= 0`, position updates atomic
- Fail-fast: Any validation failure halts execution with structured error message (no silent failures)

## Project Structure

### Documentation (this feature)

```
specs/001-readme-md/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (tech stack decisions)
├── data-model.md        # Phase 1 output (8 entities detailed)
├── quickstart.md        # Phase 1 output (getting started guide)
├── contracts/           # Phase 1 output (API schemas, config schemas)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
bollinger-band-trade/
├── src/
│   ├── models/
│   │   ├── portfolio.py         # Portfolio, Position entities
│   │   ├── trade.py              # Trade entity, trade logging
│   │   ├── stock_data.py         # Stock Data entity, OHLCV handling
│   │   └── config.py             # Backtest Configuration (Pydantic)
│   ├── indicators/
│   │   ├── bollinger.py          # Bollinger Band calculation
│   │   └── squeeze.py            # Squeeze detection logic
│   ├── signals/
│   │   ├── generator.py          # Signal generation (entry/exit)
│   │   └── risk.py               # Stop-loss, position sizing
│   ├── data/
│   │   ├── fetcher.py            # FinanceDataReader/pykrx integration
│   │   ├── validator.py          # Data validation, outlier detection
│   │   └── storage.py            # Parquet/SQLite persistence
│   ├── backtest/
│   │   ├── engine.py             # vectorbt integration, main backtest loop
│   │   └── metrics.py            # Performance Report calculation
│   ├── cli/
│   │   └── main.py               # CLI entry point (argparse/click)
│   └── utils/
│       ├── logging.py            # Structured logging setup
│       └── validation.py         # Defensive validation utilities
│
├── tests/
│   ├── unit/
│   │   ├── test_bollinger.py    # Bollinger Band calculation tests
│   │   ├── test_squeeze.py      # Squeeze detection tests
│   │   ├── test_signals.py      # Signal generation tests
│   │   └── test_risk.py         # Risk control tests
│   ├── integration/
│   │   ├── test_backtest_e2e.py # Full backtest scenarios
│   │   └── test_data_pipeline.py # Data fetch → validate → store
│   ├── contract/
│   │   ├── test_data_sources.py # FinanceDataReader/pykrx contracts
│   │   └── test_config_schema.py # Config validation contracts
│   └── fixtures/
│       ├── sample_ohlcv.csv     # Test data fixtures
│       └── configs/              # Sample configuration files
│
├── config/
│   ├── default.yaml              # Default configuration
│   └── examples/
│       ├── single_stock.yaml     # Example: single stock backtest
│       └── multi_stock.yaml      # Example: multi-stock portfolio
│
├── data/                         # Runtime data directory (gitignored)
│   ├── cache/                    # Parquet files for historical data
│   └── logs/                     # SQLite trade logs, backtest results
│
├── pyproject.toml                # Poetry/pip dependencies, project metadata
├── pytest.ini                    # pytest configuration
├── README.md                     # Project README (Korean)
└── .gitignore
```

**Structure Decision**: Single project layout selected as this is a standalone command-line tool without frontend/backend separation. All backtesting logic resides in `src/` with clear separation of concerns: data pipeline (`data/`), indicator calculations (`indicators/`), signal generation (`signals/`), and backtest orchestration (`backtest/`). Testing follows the same structure in `tests/` with unit/integration/contract separation per constitution requirements.

## Complexity Tracking

*No constitutional violations - this section is empty as all 7 principles pass without justification needed.*
